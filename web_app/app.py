"""Flask Web UI for FrameEdit."""

from __future__ import annotations

import os
import secrets
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from frameedit.pipeline import AssetType, BatchError
from frameedit.web_services.assets import AssetError, list_assets, save_asset_upload
from frameedit.web_services.carousel_panorama import (
    CarouselPanoramaError,
    render_carousel_panorama,
)
from frameedit.web_services.carousel_projects import (
    CarouselProjectError,
    carousel_output_files,
    create_carousel_project_dir,
    delete_carousel_project,
    list_carousel_projects,
    load_carousel_project,
    write_carousel_metadata,
)
from frameedit.web_services.generation import (
    ClassifiedUpload,
    classify_uploads,
    render_post_outputs,
    render_reel_output,
    normalize_category_name,
    normalize_product_name,
)
from frameedit.web_services.grid_mosaic import GridMosaicError, render_grid_mosaic
from frameedit.web_services.paths import data_dir, ensure_data_dirs, path_within
from frameedit.web_services.presets import (
    PresetError,
    create_preset,
    delete_preset,
    duplicate_preset,
    list_presets,
    load_preset,
    rename_preset,
    save_preset,
)
from frameedit.web_services.projects import (
    ProjectGridError,
    create_project_dir,
    list_projects,
    load_project,
    project_grid_candidates,
    project_grid_layout,
    project_output_files,
    save_project_grid_layout,
    write_project_metadata,
)
from frameedit.web_services.slugs import safe_filename, slugify, unique_path
from frameedit.web_services.zipfiles import create_output_zip


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATA_DIR=data_dir(),
        MAX_CONTENT_LENGTH=int(os.environ.get("WEB_UI_MAX_UPLOAD_MB", "512")) * 1024 * 1024,
        SECRET_KEY=os.environ.get("WEB_UI_SECRET_KEY") or secrets.token_hex(32),
        WEB_UI_PASSWORD=os.environ.get("WEB_UI_PASSWORD", ""),
    )
    if test_config:
        app.config.update(test_config)

    ensure_data_dirs(Path(app.config["DATA_DIR"]))
    _register_auth(app)
    _register_template_helpers(app)
    _register_routes(app)
    return app


def _register_auth(app: Flask) -> None:
    @app.before_request
    def require_login() -> None:
        password = app.config.get("WEB_UI_PASSWORD") or ""
        if not password:
            return
        allowed = {"login", "static", "favicon_ico"}
        if request.endpoint in allowed:
            return
        if session.get("authenticated"):
            return
        return redirect(url_for("login", next=request.path))


def _register_template_helpers(app: Flask) -> None:
    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {
            "presets": list_presets(Path(app.config["DATA_DIR"])),
            "auth_enabled": bool(app.config.get("WEB_UI_PASSWORD")),
            "data_root": str(Path(app.config["DATA_DIR"])),
        }

    @app.template_filter("basename")
    def basename(path: str) -> str:
        return Path(path).name

    @app.template_filter("relpath")
    def relpath(path: str | Path, base: str | Path) -> str:
        try:
            return str(Path(path).resolve().relative_to(Path(base).resolve()))
        except ValueError:
            return Path(path).name


def _register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        return render_template("all_in_one.html")

    @app.get("/favicon.ico")
    def favicon_ico():
        return send_file(Path(app.root_path) / "static" / "brand" / "favicon.ico")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not app.config.get("WEB_UI_PASSWORD"):
            return redirect(url_for("all_in_one"))
        if request.method == "POST":
            if request.form.get("password") == app.config["WEB_UI_PASSWORD"]:
                session["authenticated"] = True
                return redirect(request.args.get("next") or url_for("all_in_one"))
            flash("Incorrect password.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/all-in-one")
    def all_in_one():
        return render_template("all_in_one.html")

    @app.post("/all-in-one/preview")
    def all_in_one_preview():
        root = Path(app.config["DATA_DIR"])
        preset = _load_preset_from_form(root)
        product_name = request.form.get("product_name", "").strip()
        category_name = request.form.get("category_name", "").strip()
        if not product_name:
            flash("Product name is required.", "error")
            return redirect(url_for("all_in_one"))
        if not category_name:
            flash("Category name is required.", "error")
            return redirect(url_for("all_in_one"))
        product_name = normalize_product_name(product_name)
        category_name = normalize_category_name(category_name)

        job_dir = _new_temp_job(root, "all-in-one")
        uploads = _save_uploads(request.files.getlist("images"), job_dir / "uploads")
        if not uploads:
            flash("Upload at least one image.", "error")
            return redirect(url_for("all_in_one"))

        try:
            upload_set = classify_uploads(uploads, preset.config)
            preview_files = _render_preview_outputs(
                preset.config,
                upload_set,
                job_dir,
                product_name,
                category_name,
            )
        except (BatchError, OSError, ValueError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("all_in_one"))

        _write_job(
            job_dir,
            {
                "mode": "all-in-one",
                "preset_slug": preset.slug,
                "product_name": product_name,
                "category_name": category_name,
                "uploads": _upload_set_to_dict(upload_set),
            },
        )
        return render_template(
            "all_in_one_preview.html",
            job_id=job_dir.name,
            preset=preset,
            upload_set=upload_set,
            preview_files=preview_files,
        )

    @app.post("/all-in-one/generate")
    def all_in_one_generate():
        root = Path(app.config["DATA_DIR"])
        job_dir, job = _load_job_from_form(root)
        preset = load_preset(str(job["preset_slug"]), root)
        product_name = str(job["product_name"])
        category_name = str(job["category_name"])
        posts = [Path(item["path"]) for item in job["uploads"]["posts"]]
        reels = [Path(item["path"]) for item in job["uploads"]["reels"]]

        reel_index = _int_form("reel_index", 0)
        reel_source = reels[reel_index] if reels and 0 <= reel_index < len(reels) else None
        vignette_choices = {
            index: request.form.get(f"vignette_{index}", "center")
            for index in range(len(posts))
        }

        project_path = create_project_dir(
            brand_name=preset.name,
            brand_slug=preset.slug,
            product_name=product_name,
            root=root,
        )
        shutil.copytree(job_dir / "uploads", project_path / "uploads", dirs_exist_ok=True)
        output_paths = []
        try:
            generated_posts = render_post_outputs(
                preset.config,
                posts,
                output_dir=project_path,
                product_name=product_name,
                vignette_choices=vignette_choices,
            )
            output_paths.extend(item.path for item in generated_posts)
            if reel_source:
                reel = render_reel_output(
                    preset.config,
                    reel_source,
                    output_dir=project_path,
                    product_name=product_name,
                    category_name=category_name,
                )
                output_paths.append(reel.path)
        except (BatchError, OSError, ValueError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("all_in_one"))

        archive_root = f"{slugify(product_name)}-{preset.slug}"
        zip_path = project_path / f"{archive_root}.zip"
        create_output_zip(project_path, zip_path=zip_path, archive_root=archive_root)
        project = write_project_metadata(
            project_path,
            brand_name=preset.name,
            brand_slug=preset.slug,
            product_name=product_name,
            zip_path=zip_path,
            outputs=output_paths,
        )
        flash("Project generated.", "success")
        return redirect(
            url_for(
                "project_detail",
                brand_slug=project.brand_slug,
                project_slug=project.path.name,
            )
        )

    @app.post("/preview/post-vignette")
    def preview_post_vignette():
        root = Path(app.config["DATA_DIR"])
        job_dir, job = _load_job_from_form(root)
        try:
            post_index = int(request.form.get("post_index", ""))
        except ValueError:
            return jsonify({"error": "Invalid post index."}), 400

        posts = [Path(item["path"]) for item in job["uploads"]["posts"]]
        if post_index < 0 or post_index >= len(posts):
            return jsonify({"error": "Post index out of range."}), 400

        try:
            preset = load_preset(str(job["preset_slug"]), root)
            product_name = str(job.get("product_name") or "")
            stems = _post_output_stems(product_name, posts)
            generated = render_post_outputs(
                preset.config,
                [posts[post_index]],
                output_dir=job_dir / "preview",
                product_name=product_name or "posts",
                vignette_choices={0: request.form.get("vignette", "center")},
                include_webp=False,
                output_stems=[stems[post_index]],
            )[0]
        except (BatchError, OSError, ValueError, PresetError) as exc:
            return jsonify({"error": str(exc)}), 400

        relative_path = str(generated.path.resolve().relative_to(job_dir.resolve()))
        return jsonify(
            {
                "image_url": url_for(
                    "temp_file",
                    job_id=job_dir.name,
                    relative_path=relative_path,
                    v=uuid4().hex,
                )
            }
        )

    @app.get("/posts")
    def posts_edit():
        return render_template("posts.html")

    @app.post("/posts/preview")
    def posts_preview():
        root = Path(app.config["DATA_DIR"])
        preset = _load_preset_from_form(root)
        product_name = request.form.get("product_name", "").strip()
        job_dir = _new_temp_job(root, "posts")
        uploads = _save_uploads(request.files.getlist("images"), job_dir / "uploads")
        if not uploads:
            flash("Upload at least one image.", "error")
            return redirect(url_for("posts_edit"))
        upload_set = classify_uploads(uploads, preset.config)
        if upload_set.reels:
            flash("Posts Edit accepts only 3:4 post images.", "error")
        if upload_set.unsupported:
            flash("Unsupported files were rejected.", "error")
        posts = upload_set.posts
        preview_files = render_post_outputs(
            preset.config,
            [item.path for item in posts],
            output_dir=job_dir / "preview",
            product_name=product_name or "posts",
            output_stems=_post_output_stems(product_name, posts),
        )
        _write_job(
            job_dir,
            {
                "mode": "posts",
                "preset_slug": preset.slug,
                "product_name": product_name,
                "uploads": _upload_set_to_dict(upload_set),
            },
        )
        return render_template(
            "posts_preview.html",
            job_id=job_dir.name,
            preset=preset,
            upload_set=upload_set,
            preview_files=preview_files,
        )

    @app.post("/posts/generate")
    def posts_generate():
        root = Path(app.config["DATA_DIR"])
        job_dir, job = _load_job_from_form(root)
        preset = load_preset(str(job["preset_slug"]), root)
        product_name = str(job["product_name"])
        posts = [Path(item["path"]) for item in job["uploads"]["posts"]]
        vignette_choices = {
            index: request.form.get(f"vignette_{index}", "center")
            for index in range(len(posts))
        }
        output_dir = job_dir / "outputs"
        generated = render_post_outputs(
            preset.config,
            posts,
            output_dir=output_dir,
            product_name=product_name or "posts",
            vignette_choices=vignette_choices,
            output_stems=_post_output_stems(product_name, [Path(item["path"]) for item in job["uploads"]["posts"]]),
        )
        archive_root = f"{slugify(product_name, fallback='posts')}-posts"
        zip_path = output_dir / f"{archive_root}.zip"
        create_output_zip(output_dir, zip_path=zip_path, archive_root=archive_root)
        return render_template(
            "temp_result.html",
            title="Posts Generated",
            job_id=job_dir.name,
            files=generated,
            zip_path=zip_path,
        )

    @app.get("/grid")
    def grid_mosaic():
        return render_template("grid_mosaic.html")

    @app.post("/grid/generate")
    def grid_mosaic_generate():
        root = Path(app.config["DATA_DIR"])
        mosaic_name = request.form.get("mosaic_name", "").strip() or "Grid Mosaic"
        tile_format = request.form.get("tile_format", "profile_3x4")
        source_mode = request.form.get("source_mode", "bleed")
        fit_mode = request.form.get("fit_mode", "crop")
        job_dir = _new_temp_job(root, "grid")
        uploads = _save_uploads(request.files.getlist("image"), job_dir / "uploads")
        if len(uploads) != 1:
            flash("Upload exactly one horizontal source image.", "error")
            return redirect(url_for("grid_mosaic"))

        try:
            result = render_grid_mosaic(
                uploads[0],
                output_dir=job_dir / "outputs",
                mosaic_name=mosaic_name,
                tile_format=tile_format,
                source_mode=source_mode,
                fit_mode=fit_mode,
            )
        except (GridMosaicError, OSError, ValueError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("grid_mosaic"))

        archive_root = f"{slugify(mosaic_name, fallback='grid-mosaic')}-grid-mosaic"
        zip_path = job_dir / "outputs" / f"{archive_root}.zip"
        create_output_zip(job_dir / "outputs", zip_path=zip_path, archive_root=archive_root)
        return render_template(
            "grid_mosaic_result.html",
            job_id=job_dir.name,
            result=result,
            zip_path=zip_path,
        )

    @app.get("/carousel")
    def carousel_panorama():
        root = Path(app.config["DATA_DIR"])
        query = request.args.get("q", "").strip()
        return render_template(
            "carousel_panorama.html",
            carousels=list_carousel_projects(root=root, query=query),
            query=query,
        )

    @app.post("/carousel/generate")
    def carousel_panorama_generate():
        root = Path(app.config["DATA_DIR"])
        carousel_name = request.form.get("carousel_name", "").strip() or "Carousel Panorama"
        slide_format = request.form.get("slide_format", "portrait_3x4")
        slide_count = _int_form("slide_count", 3)
        fit_mode = request.form.get("fit_mode", "crop")
        job_dir = _new_temp_job(root, "carousel")
        uploads = _save_uploads(request.files.getlist("image"), job_dir / "uploads")
        if len(uploads) != 1:
            shutil.rmtree(job_dir, ignore_errors=True)
            flash("Upload exactly one horizontal source image.", "error")
            return redirect(url_for("carousel_panorama"))

        project_path = create_carousel_project_dir(carousel_name, root=root)
        shutil.copytree(job_dir / "uploads", project_path / "uploads", dirs_exist_ok=True)
        source = project_path / "uploads" / uploads[0].name
        try:
            result = render_carousel_panorama(
                source,
                output_dir=project_path,
                carousel_name=carousel_name,
                slide_count=slide_count,
                slide_format=slide_format,
                fit_mode=fit_mode,
            )
        except (CarouselPanoramaError, OSError, ValueError) as exc:
            shutil.rmtree(project_path, ignore_errors=True)
            shutil.rmtree(job_dir, ignore_errors=True)
            flash(str(exc), "error")
            return redirect(url_for("carousel_panorama"))

        archive_root = f"{slugify(carousel_name, fallback='carousel-panorama')}-carousel-panorama"
        zip_path = project_path / f"{archive_root}.zip"
        create_output_zip(project_path, zip_path=zip_path, archive_root=archive_root)
        carousel = write_carousel_metadata(
            project_path,
            carousel_name=carousel_name,
            source_path=source,
            zip_path=zip_path,
            result=result,
        )
        shutil.rmtree(job_dir, ignore_errors=True)
        flash("Carousel saved.", "success")
        return render_template(
            "carousel_panorama_result.html",
            carousel=carousel,
            files=carousel_output_files(carousel),
        )

    @app.get("/carousel/<carousel_slug>")
    def carousel_panorama_detail(carousel_slug: str):
        root = Path(app.config["DATA_DIR"])
        carousel_path = root / "carousels" / carousel_slug
        if not path_within(carousel_path, root / "carousels"):
            abort(404)
        if not (carousel_path / "carousel.yaml").exists():
            abort(404)
        carousel = load_carousel_project(carousel_path)
        return render_template(
            "carousel_panorama_result.html",
            carousel=carousel,
            files=carousel_output_files(carousel),
        )

    @app.post("/carousel/<carousel_slug>/delete")
    def carousel_panorama_delete(carousel_slug: str):
        try:
            delete_carousel_project(carousel_slug, root=Path(app.config["DATA_DIR"]))
            flash("Carousel deleted.", "success")
        except CarouselProjectError as exc:
            flash(str(exc), "error")
        return redirect(url_for("carousel_panorama"))

    @app.get("/reel-cover")
    def reel_cover_edit():
        return render_template("reel_cover.html")

    @app.post("/reel-cover/preview")
    def reel_cover_preview():
        root = Path(app.config["DATA_DIR"])
        preset = _load_preset_from_form(root)
        product_name = request.form.get("product_name", "").strip()
        category_name = request.form.get("category_name", "").strip()
        if not product_name or not category_name:
            flash("Product name and category name are required.", "error")
            return redirect(url_for("reel_cover_edit"))
        product_name = normalize_product_name(product_name)
        category_name = normalize_category_name(category_name)
        job_dir = _new_temp_job(root, "reel")
        uploads = _save_uploads(request.files.getlist("image"), job_dir / "uploads")
        if len(uploads) != 1:
            flash("Upload exactly one reel-cover image.", "error")
            return redirect(url_for("reel_cover_edit"))
        upload_set = classify_uploads(uploads, preset.config)
        if not upload_set.reels or upload_set.posts or upload_set.unsupported:
            flash("Reel Cover Edit accepts one 9:16 image only.", "error")
            return redirect(url_for("reel_cover_edit"))
        generated = render_reel_output(
            preset.config,
            upload_set.reels[0].path,
            output_dir=job_dir / "outputs",
            product_name=product_name,
            category_name=category_name,
        )
        return render_template(
            "temp_result.html",
            title="Reel Cover Generated",
            job_id=job_dir.name,
            files=[generated],
            zip_path=None,
        )

    @app.get("/recent")
    def recent_projects():
        root = Path(app.config["DATA_DIR"])
        query = request.args.get("q", "").strip()
        brand_slug = request.args.get("brand", "").strip()
        projects = list_projects(root=root, query=query, brand_slug=brand_slug)
        return render_template(
            "recent.html",
            projects=projects,
            query=query,
            selected_brand=brand_slug,
        )

    @app.get("/projects/<brand_slug>/<project_slug>")
    def project_detail(brand_slug: str, project_slug: str):
        project_path = Path(app.config["DATA_DIR"]) / "projects" / brand_slug / project_slug
        if not path_within(project_path, Path(app.config["DATA_DIR"]) / "projects"):
            abort(404)
        if not (project_path / "project.yaml").exists():
            abort(404)
        project = load_project(project_path)
        grid_candidates = project_grid_candidates(project)
        grid_candidate_map = {candidate.relative_path: candidate for candidate in grid_candidates}
        grid_items = [
            grid_candidate_map[path]
            for path in project_grid_layout(project)
            if path in grid_candidate_map
        ]
        return render_template(
            "project_detail.html",
            project=project,
            files=project_output_files(project),
            grid_candidates=grid_candidates,
            grid_items=grid_items,
        )

    @app.post("/projects/<brand_slug>/<project_slug>/grid-layout")
    def project_grid_layout_save(brand_slug: str, project_slug: str):
        project_path = Path(app.config["DATA_DIR"]) / "projects" / brand_slug / project_slug
        if not path_within(project_path, Path(app.config["DATA_DIR"]) / "projects"):
            abort(404)
        if not (project_path / "project.yaml").exists():
            abort(404)

        payload = request.get_json(silent=True) or {}
        layout = payload.get("layout")
        if layout is None:
            layout = request.form.getlist("layout")
        if not isinstance(layout, list):
            return jsonify({"error": "Grid layout must be a list."}), 400
        try:
            project = save_project_grid_layout(project_path, [str(item) for item in layout])
        except ProjectGridError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"layout": project_grid_layout(project)})

    @app.get("/settings")
    def settings():
        root = Path(app.config["DATA_DIR"])
        return render_template(
            "settings.html",
            asset_groups={
                "logos": list_assets("logos", root),
                "fonts": list_assets("fonts", root),
                "vignettes": list_assets("vignettes", root),
            },
        )

    @app.post("/settings/presets/create")
    def settings_create_preset():
        try:
            preset = create_preset(request.form.get("name", "New Brand"), Path(app.config["DATA_DIR"]))
            flash("Preset created.", "success")
            return redirect(url_for("settings_edit_preset", slug=preset.slug))
        except PresetError as exc:
            flash(str(exc), "error")
            return redirect(url_for("settings"))

    @app.get("/settings/presets/<slug>")
    def settings_edit_preset(slug: str):
        try:
            preset = load_preset(slug, Path(app.config["DATA_DIR"]))
        except PresetError as exc:
            flash(str(exc), "error")
            return redirect(url_for("settings"))
        return render_template("preset_form.html", preset=preset, raw=preset.raw)

    @app.post("/settings/presets/<slug>")
    def settings_save_preset(slug: str):
        raw = _preset_form_to_raw(request.form)
        try:
            preset = save_preset(slug, raw, Path(app.config["DATA_DIR"]))
        except PresetError as exc:
            flash(str(exc), "error")
            return render_template("preset_form.html", preset=None, raw=raw), 400
        flash("Preset saved.", "success")
        return redirect(url_for("settings_edit_preset", slug=preset.slug))

    @app.post("/settings/presets/<slug>/duplicate")
    def settings_duplicate_preset(slug: str):
        try:
            preset = duplicate_preset(slug, Path(app.config["DATA_DIR"]))
            flash("Preset duplicated.", "success")
            return redirect(url_for("settings_edit_preset", slug=preset.slug))
        except PresetError as exc:
            flash(str(exc), "error")
            return redirect(url_for("settings"))

    @app.post("/settings/presets/<slug>/rename")
    def settings_rename_preset(slug: str):
        try:
            preset = rename_preset(slug, request.form.get("name", ""), Path(app.config["DATA_DIR"]))
            flash("Preset renamed.", "success")
            return redirect(url_for("settings_edit_preset", slug=preset.slug))
        except PresetError as exc:
            flash(str(exc), "error")
            return redirect(url_for("settings_edit_preset", slug=slug))

    @app.post("/settings/presets/<slug>/delete")
    def settings_delete_preset(slug: str):
        try:
            delete_preset(slug, Path(app.config["DATA_DIR"]))
            flash("Preset deleted.", "success")
        except PresetError as exc:
            flash(str(exc), "error")
        return redirect(url_for("settings"))

    @app.post("/settings/assets/<kind>")
    def settings_upload_asset(kind: str):
        try:
            save_asset_upload(request.files["asset"], kind, Path(app.config["DATA_DIR"]))
            flash("Asset uploaded.", "success")
        except (KeyError, AssetError) as exc:
            flash(str(exc), "error")
        return redirect(url_for("settings"))

    @app.get("/download/project/<brand_slug>/<project_slug>/zip")
    def download_project_zip(brand_slug: str, project_slug: str):
        project_path = Path(app.config["DATA_DIR"]) / "projects" / brand_slug / project_slug
        if not (project_path / "project.yaml").exists():
            abort(404)
        project = load_project(project_path)
        if not project.zip_path or not project.zip_path.exists():
            abort(404)
        return send_file(project.zip_path, as_attachment=True)

    @app.get("/file/project/<brand_slug>/<project_slug>/<path:relative_path>")
    def project_file(brand_slug: str, project_slug: str, relative_path: str):
        base = Path(app.config["DATA_DIR"]) / "projects" / brand_slug / project_slug
        return _send_safe_file(base, relative_path, as_attachment=False)

    @app.get("/download/project-file/<brand_slug>/<project_slug>/<path:relative_path>")
    def download_project_file(brand_slug: str, project_slug: str, relative_path: str):
        base = Path(app.config["DATA_DIR"]) / "projects" / brand_slug / project_slug
        return _send_safe_file(base, relative_path, as_attachment=True)

    @app.get("/download/carousel/<carousel_slug>/zip")
    def download_carousel_zip(carousel_slug: str):
        carousel_path = Path(app.config["DATA_DIR"]) / "carousels" / carousel_slug
        if not path_within(carousel_path, Path(app.config["DATA_DIR"]) / "carousels"):
            abort(404)
        if not (carousel_path / "carousel.yaml").exists():
            abort(404)
        carousel = load_carousel_project(carousel_path)
        if not carousel.zip_path or not carousel.zip_path.exists():
            abort(404)
        return send_file(carousel.zip_path, as_attachment=True)

    @app.get("/file/carousel/<carousel_slug>/<path:relative_path>")
    def carousel_file(carousel_slug: str, relative_path: str):
        base = Path(app.config["DATA_DIR"]) / "carousels" / carousel_slug
        if not (base / "carousel.yaml").exists():
            abort(404)
        return _send_safe_file(base, relative_path, as_attachment=False)

    @app.get("/download/carousel-file/<carousel_slug>/<path:relative_path>")
    def download_carousel_file(carousel_slug: str, relative_path: str):
        base = Path(app.config["DATA_DIR"]) / "carousels" / carousel_slug
        if not (base / "carousel.yaml").exists():
            abort(404)
        return _send_safe_file(base, relative_path, as_attachment=True)

    @app.get("/file/temp/<job_id>/<path:relative_path>")
    def temp_file(job_id: str, relative_path: str):
        base = Path(app.config["DATA_DIR"]) / "temp" / job_id
        return _send_safe_file(base, relative_path, as_attachment=False)

    @app.get("/download/temp/<job_id>/<path:relative_path>")
    def download_temp_file(job_id: str, relative_path: str):
        base = Path(app.config["DATA_DIR"]) / "temp" / job_id
        return _send_safe_file(base, relative_path, as_attachment=True)


def _load_preset_from_form(root: Path):
    slug = request.form.get("preset_slug") or request.form.get("preset") or "starter-brand"
    return load_preset(slug, root)


def _new_temp_job(root: Path, prefix: str) -> Path:
    job_dir = root / "temp" / f"{prefix}-{uuid4().hex}"
    job_dir.mkdir(parents=True)
    return job_dir


def _save_uploads(files: list[Any], target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for upload in files:
        filename = getattr(upload, "filename", "") or ""
        if not filename:
            continue
        target = unique_path(target_dir, safe_filename(filename, fallback_stem="image"))
        upload.save(target)
        saved.append(target)
    return saved


def _render_preview_outputs(
    config,
    upload_set,
    job_dir: Path,
    product_name: str,
    category_name: str,
) -> list[Any]:
    previews = []
    if upload_set.posts:
        previews.extend(
            render_post_outputs(
                config,
                [item.path for item in upload_set.posts],
                output_dir=job_dir / "preview",
                product_name=product_name,
                include_webp=False,
            )
        )
    if upload_set.reels:
        previews.append(
            render_reel_output(
                config,
                upload_set.reels[0].path,
                output_dir=job_dir / "preview",
                product_name=product_name,
                category_name=category_name,
            )
        )
    return previews


def _write_job(job_dir: Path, data: dict[str, Any]) -> None:
    (job_dir / "job.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _load_job_from_form(root: Path) -> tuple[Path, dict[str, Any]]:
    job_id = request.form.get("job_id", "")
    job_dir = root / "temp" / job_id
    if not path_within(job_dir, root / "temp") or not (job_dir / "job.yaml").exists():
        abort(404)
    raw = yaml.safe_load((job_dir / "job.yaml").read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        abort(404)
    return job_dir, raw


def _upload_set_to_dict(upload_set) -> dict[str, list[dict[str, Any]]]:
    return {
        "posts": [_classified_to_dict(item) for item in upload_set.posts],
        "reels": [_classified_to_dict(item) for item in upload_set.reels],
        "unsupported": [_classified_to_dict(item) for item in upload_set.unsupported],
    }


def _classified_to_dict(item: ClassifiedUpload) -> dict[str, Any]:
    data = asdict(item)
    data["path"] = str(item.path)
    data["asset_type"] = item.asset_type.value
    return data


def _int_form(name: str, default: int) -> int:
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


def _post_output_stems(product_name: str, posts: list[Any]) -> list[str]:
    if product_name.strip():
        product_slug = slugify(product_name, fallback="posts")
        return [f"{product_slug}-post-{index:02d}" for index in range(1, len(posts) + 1)]

    stems = []
    seen: dict[str, int] = {}
    for post in posts:
        path = post.path if hasattr(post, "path") else Path(post)
        stem = slugify(path.stem, fallback="post")
        count = seen.get(stem, 0) + 1
        seen[stem] = count
        stems.append(stem if count == 1 else f"{stem}-{count}")
    return stems


def _send_safe_file(base: Path, relative_path: str, *, as_attachment: bool):
    target = base / relative_path
    if not path_within(target, base) or not target.exists() or not target.is_file():
        abort(404)
    return send_file(target, as_attachment=as_attachment)


def _preset_form_to_raw(form) -> dict[str, Any]:
    return {
        "brand": {
            "name": form.get("brand_name", "Brand").strip(),
            "slug": slugify(form.get("brand_name", "brand")),
        },
        "input_dir": form.get("input_dir", "../../input").strip(),
        "output_dir": form.get("output_dir", "../../output").strip(),
        "scan_recursive": _checkbox(form, "scan_recursive"),
        "aspect_ratio_tolerance": _float_field(form, "aspect_ratio_tolerance", 0.02),
        "overwrite": _checkbox(form, "overwrite"),
        "supported_extensions": [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"],
        "post": {
            "size": [_int_field(form, "post_width", 1080), _int_field(form, "post_height", 1440)],
            "default_vignette": form.get("post_default_vignette", "centered"),
            "vignette_opacity": _float_field(form, "post_vignette_opacity", 1.0),
            "vignettes": {
                "centered": form.get("vignette_centered", "").strip(),
                "top": form.get("vignette_top", "").strip(),
                "bottom": form.get("vignette_bottom", "").strip(),
            },
            "logo": _logo_form(form, "post"),
        },
        "webp_variant": {
            "enabled": _checkbox(form, "webp_enabled"),
            "include_logo": _checkbox(form, "webp_include_logo"),
            "lossless": _checkbox(form, "webp_lossless"),
            "quality": _int_field(form, "webp_quality", 100),
            "method": _int_field(form, "webp_method", 6),
        },
        "reel_cover": {
            "size": [_int_field(form, "reel_width", 1080), _int_field(form, "reel_height", 1920)],
            "background_blur": {
                "enabled": _checkbox(form, "blur_enabled"),
                "intensity": _float_field(form, "blur_intensity", 0.06),
                "max_radius": _float_field(form, "blur_max_radius", 100),
            },
            "black_overlay": {
                "file": form.get("black_overlay_file", "").strip(),
                "opacity": _float_field(form, "black_overlay_opacity", 0.6),
            },
            "logo": _logo_form(form, "reel"),
            "product_name": _text_form(form, "product", default_auto_multiline=True),
            "category_name": _text_form(form, "category", default_auto_multiline=False),
        },
    }


def _logo_form(form, prefix: str) -> dict[str, Any]:
    return {
        "file": form.get(f"{prefix}_logo_file", "").strip(),
        "scale": _float_field(form, f"{prefix}_logo_scale", 0.2),
        "center": [
            _int_field(form, f"{prefix}_logo_center_x", 540),
            _int_field(form, f"{prefix}_logo_center_y", 100),
        ],
        "opacity": _float_field(form, f"{prefix}_logo_opacity", 1.0),
    }


def _text_form(form, prefix: str, *, default_auto_multiline: bool) -> dict[str, Any]:
    return {
        "text": form.get(f"{prefix}_text", "").strip(),
        "font": form.get(f"{prefix}_font", "").strip(),
        "size": _int_field(form, f"{prefix}_size", 100),
        "center": [
            _int_field(form, f"{prefix}_center_x", 540),
            _int_field(form, f"{prefix}_center_y", 950),
        ],
        "color": form.get(f"{prefix}_color", "#e1d9cb").strip(),
        "auto_multiline": _checkbox(form, f"{prefix}_auto_multiline", default_auto_multiline),
        "max_width": _int_or_blank(form, f"{prefix}_max_width"),
        "line_spacing": _float_field(form, f"{prefix}_line_spacing", 1.05),
        "letter_spacing": _float_field(form, f"{prefix}_letter_spacing", 0),
        "last_word_second_line": _checkbox(form, f"{prefix}_last_word_second_line"),
    }


def _checkbox(form, name: str, default: bool = False) -> bool:
    values = form.getlist(name)
    if not values:
        return default
    return any(value in {"on", "true", "1", "yes"} for value in values)


def _int_field(form, name: str, default: int) -> int:
    try:
        return int(form.get(name, default))
    except (TypeError, ValueError):
        return default


def _int_or_blank(form, name: str) -> int | None:
    value = form.get(name, "")
    if value == "":
        return None
    return _int_field(form, name, 0)


def _float_field(form, name: str, default: float) -> float:
    try:
        return float(form.get(name, default))
    except (TypeError, ValueError):
        return default


app = create_app()
