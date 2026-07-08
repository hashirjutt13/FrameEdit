from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from frameedit.web_services.carousel_projects import list_carousel_projects
from frameedit.web_services.presets import load_preset
from frameedit.web_services.projects import create_project_dir, list_projects, write_project_metadata
from web_app.app import create_app

from web_helpers import image_upload, write_test_preset


@pytest.fixture()
def app(tmp_path: Path):
    root = tmp_path / "data"
    write_test_preset(root)
    return create_app(
        {
            "TESTING": True,
            "DATA_DIR": root,
            "WEB_UI_PASSWORD": "",
            "SECRET_KEY": "test-secret",
        }
    )


def _job_id(response) -> str:
    match = re.search(rb'name="job_id" value="([^"]+)"', response.data)
    assert match
    return match.group(1).decode()


def test_homepage_opens_all_in_one(app) -> None:
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"FrameEdit" in response.data
    assert b'alt="FrameEdit"' in response.data
    assert b"brand/frameedit-logo.svg" in response.data
    assert b"brand/frameedit-favicon.svg" in response.data
    assert b"brand/favicon-32.png" in response.data
    assert b"/favicon.ico" in response.data
    assert b"All In One Edit" in response.data
    assert b"Previous Work" in response.data
    assert b'href="/recent"' in response.data
    assert b'>Recent</a>' not in response.data
    assert b'nav-link active' in response.data


def test_favicon_ico_route(app) -> None:
    client = app.test_client()

    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.mimetype in {"image/x-icon", "image/vnd.microsoft.icon"}


def test_previous_work_is_under_all_in_one_nav(app) -> None:
    client = app.test_client()

    response = client.get("/recent")

    assert response.status_code == 200
    assert b"Previous Work" in response.data
    assert b'<a class="nav-link active" href="/all-in-one">All In One</a>' in response.data
    assert b'>Recent</a>' not in response.data


def test_auth_gate_when_password_enabled(tmp_path: Path) -> None:
    root = tmp_path / "data"
    write_test_preset(root)
    app = create_app(
        {
            "TESTING": True,
            "DATA_DIR": root,
            "WEB_UI_PASSWORD": "secret",
            "SECRET_KEY": "test-secret",
        }
    )
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client.get("/all-in-one")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client.post("/login", data={"password": "secret"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"All In One Edit" in response.data


def test_settings_imports_preset_json_and_local_assets(app) -> None:
    client = app.test_client()

    settings = client.get("/settings")
    assert settings.status_code == 200
    assert b"Import JSON" in settings.data
    assert b"Import Local Logos and Fonts" in settings.data

    raw = yaml.safe_load((app.config["DATA_DIR"] / "presets" / "test-brand.yaml").read_text(encoding="utf-8"))
    raw["brand"] = {"name": "Imported Brand", "slug": "imported-brand"}
    raw["post"]["logo"]["scale"] = 0.31
    imported = client.post(
        "/settings/presets/import-json",
        data={"target_slug": "__new__", "preset_json_text": json.dumps(raw)},
        follow_redirects=True,
    )
    assert imported.status_code == 200
    assert b"Preset imported." in imported.data
    assert load_preset("imported-brand", app.config["DATA_DIR"]).config.post.logo.scale == 0.31

    seeded = client.post("/settings/assets/seed-local", follow_redirects=True)
    assert seeded.status_code == 200
    assert b"local assets" in seeded.data
    assert (app.config["DATA_DIR"] / "assets" / "logos" / "logo-placeholder.png").exists()


def test_all_in_one_preview_and_generate_zip(app) -> None:
    client = app.test_client()
    response = client.post(
        "/all-in-one/preview",
        data={
            "preset_slug": "test-brand",
            "product_name": "eclat console",
            "category_name": "console tables",
            "images": [
                image_upload("chair.png", (750, 1000), "red"),
                image_upload("reel.png", (900, 1600), "blue"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"Preview Batch" in response.data
    assert b'<article class="preview-card">' in response.data
    first_card = response.data.split(b'<article class="preview-card">', 1)[1].split(b"</article>", 1)[0]
    assert b'name="vignette_0"' in first_card
    assert b"js-vignette-live" in first_card
    job_id = _job_id(response)
    job_yaml = app.config["DATA_DIR"] / "temp" / job_id / "job.yaml"
    job_text = job_yaml.read_text(encoding="utf-8")
    assert "product_name: ECLAT CONSOLE" in job_text
    assert "category_name: Console Tables" in job_text

    live_preview = client.post(
        "/preview/post-vignette",
        data={"job_id": job_id, "post_index": "0", "vignette": "top"},
    )
    assert live_preview.status_code == 200
    assert live_preview.json
    assert "image_url" in live_preview.json
    assert "v=" in live_preview.json["image_url"]

    response = client.post(
        "/all-in-one/generate",
        data={"job_id": job_id, "reel_index": "0", "vignette_0": "top"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Download ZIP" in response.data
    assert b"eclat-console-post-01.png" in response.data
    assert b"eclat-console-reel-cover.png" in response.data
    assert b"Instagram Grid Preview" in response.data
    assert b"data-instagram-grid" in response.data
    assert b'data-crop-mode="profile"' in response.data
    assert b"Profile Grid 3:4" in response.data
    assert b"Feed Crop 4:5" in response.data

    project = list_projects(root=app.config["DATA_DIR"])[0]
    save_grid = client.post(
        f"/projects/{project.brand_slug}/{project.path.name}/grid-layout",
        json={
            "layout": [
                "reel_cover/eclat-console-reel-cover.png",
                "posts_instagram/eclat-console-post-01.png",
                "posts_instagram/eclat-console-post-01.png",
            ],
        },
    )
    assert save_grid.status_code == 200
    assert save_grid.json
    assert save_grid.json["layout"][0] == "reel_cover/eclat-console-reel-cover.png"
    assert "grid_layout:" in (project.path / "project.yaml").read_text(encoding="utf-8")

    bad_grid = client.post(
        f"/projects/{project.brand_slug}/{project.path.name}/grid-layout",
        json={"layout": ["../outside.png", "posts_instagram/eclat-console-post-01.png"]},
    )
    assert bad_grid.status_code == 400


def test_all_in_one_warnings_for_no_reel_multiple_reels_and_unsupported(app) -> None:
    client = app.test_client()

    no_reel = client.post(
        "/all-in-one/preview",
        data={
            "preset_slug": "test-brand",
            "product_name": "CHAIR",
            "category_name": "Seating",
            "images": [image_upload("chair.png", (750, 1000), "red")],
        },
        content_type="multipart/form-data",
    )
    assert b"No reel-cover image found." in no_reel.data

    multiple = client.post(
        "/all-in-one/preview",
        data={
            "preset_slug": "test-brand",
            "product_name": "CHAIR",
            "category_name": "Seating",
            "images": [
                image_upload("reel-a.png", (900, 1600), "blue"),
                image_upload("reel-b.png", (900, 1600), "green"),
            ],
        },
        content_type="multipart/form-data",
    )
    assert b"More than one 9:16 image found" in multiple.data

    unsupported = client.post(
        "/all-in-one/preview",
        data={
            "preset_slug": "test-brand",
            "product_name": "CHAIR",
            "category_name": "Seating",
            "images": [image_upload("square.png", (1000, 1000), "purple")],
        },
        content_type="multipart/form-data",
    )
    assert b"Unsupported uploads" in unsupported.data


def test_project_detail_grid_empty_state_without_reel(app) -> None:
    client = app.test_client()
    root = app.config["DATA_DIR"]
    project_path = create_project_dir(
        brand_name="Test Brand",
        brand_slug="test-brand",
        product_name="POST ONLY",
        root=root,
    )
    output = project_path / "posts_instagram" / "post-only-post-01.png"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"fake")
    write_project_metadata(
        project_path,
        brand_name="Test Brand",
        brand_slug="test-brand",
        product_name="POST ONLY",
        zip_path=None,
        outputs=[output],
    )

    response = client.get(f"/projects/test-brand/{project_path.name}")

    assert response.status_code == 200
    assert b"Instagram Grid Preview" in response.data
    assert b"at least one Instagram post PNG and one reel cover PNG" in response.data


def test_posts_and_reel_one_off_flows(app) -> None:
    client = app.test_client()
    posts_preview = client.post(
        "/posts/preview",
        data={
            "preset_slug": "test-brand",
            "product_name": "",
            "images": [image_upload("post.png", (750, 1000), "red")],
        },
        content_type="multipart/form-data",
    )
    assert posts_preview.status_code == 200
    first_card = posts_preview.data.split(b'<article class="preview-card">', 1)[1].split(b"</article>", 1)[0]
    assert b'name="vignette_0"' in first_card
    assert b"js-vignette-live" in first_card
    job_id = _job_id(posts_preview)
    live_preview = client.post(
        "/preview/post-vignette",
        data={"job_id": job_id, "post_index": "0", "vignette": "bottom"},
    )
    assert live_preview.status_code == 200
    assert live_preview.json
    assert "image_url" in live_preview.json
    posts_result = client.post(
        "/posts/generate",
        data={"job_id": job_id, "vignette_0": "bottom"},
    )
    assert posts_result.status_code == 200
    assert b"Download ZIP" in posts_result.data
    assert b"post.png" in posts_result.data

    reel_result = client.post(
        "/reel-cover/preview",
        data={
            "preset_slug": "test-brand",
            "product_name": "SIDE TABLE",
            "category_name": "Tables",
            "image": [image_upload("reel.png", (900, 1600), "blue")],
        },
        content_type="multipart/form-data",
    )
    assert reel_result.status_code == 200
    assert b"Reel Cover Generated" in reel_result.data


def test_grid_mosaic_flow(app) -> None:
    client = app.test_client()

    form = client.get("/grid")
    assert form.status_code == 200
    assert b"Grid Mosaic" in form.data
    assert b"3240 x 1440" in form.data
    assert b"3:4 profile-native source" in form.data
    assert b"3106 x 1350" in form.data
    assert b"3039 x 1350" not in form.data
    assert b"data-grid-source-mode" in form.data
    assert b'nav-link active' in form.data

    result = client.post(
        "/grid/generate",
        data={
            "mosaic_name": "Room Launch",
            "tile_format": "profile_3x4",
            "source_mode": "profile",
            "fit_mode": "crop",
            "image": [image_upload("grid.png", (3240, 1440), "red")],
        },
        content_type="multipart/form-data",
    )

    assert result.status_code == 200
    assert b"Grid Mosaic Generated" in result.data
    assert b"1080 x 1440" in result.data
    assert b"Upload 01" in result.data
    assert b"Column 3" in result.data
    assert b"Download ZIP" in result.data
    assert b"room-launch-upload-03-col-01.png" in result.data


def test_carousel_panorama_flow(app) -> None:
    client = app.test_client()

    form = client.get("/carousel")
    assert form.status_code == 200
    assert b"Carousel Panorama" in form.data
    assert b"Recent Carousels" in form.data
    assert b"No saved carousels yet." in form.data
    assert b"1080 x 1440" in form.data
    assert b"Recommended source canvas" in form.data
    assert b"3240 x 1440" in form.data
    assert b"ratio 9:4" in form.data
    assert b"Only this ratio is accepted." in form.data
    assert b'nav-link active' in form.data

    rejected = client.post(
        "/carousel/generate",
        data={
            "carousel_name": "Wrong Way",
            "slide_count": "3",
            "slide_format": "portrait_3x4",
            "fit_mode": "crop",
            "image": [image_upload("vertical.png", (1080, 1440), "red")],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert rejected.status_code == 200
    assert b"horizontal source image" in rejected.data
    assert not list_carousel_projects(root=app.config["DATA_DIR"])

    wrong_ratio = client.post(
        "/carousel/generate",
        data={
            "carousel_name": "Wrong Ratio",
            "slide_count": "3",
            "slide_format": "portrait_3x4",
            "fit_mode": "crop",
            "image": [image_upload("wide.png", (1920, 1080), "red")],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert wrong_ratio.status_code == 200
    assert b"must match the recommended 9:4 canvas" in wrong_ratio.data
    assert not list_carousel_projects(root=app.config["DATA_DIR"])

    result = client.post(
        "/carousel/generate",
        data={
            "carousel_name": "Room Launch",
            "slide_count": "3",
            "slide_format": "portrait_3x4",
            "fit_mode": "crop",
            "image": [image_upload("panorama.png", (3240, 1440), "red")],
        },
        content_type="multipart/form-data",
    )

    assert result.status_code == 200
    assert b"Room Launch" in result.data
    assert b"3 slides" in result.data
    assert b"Slide 01" in result.data
    assert b"Download ZIP" in result.data
    assert b"room-launch-slide-01.png" in result.data

    saved = list_carousel_projects(root=app.config["DATA_DIR"])
    assert len(saved) == 1
    carousel = saved[0]
    assert carousel.name == "Room Launch"
    assert carousel.slide_count == 3
    assert (carousel.path / "carousel.yaml").exists()
    assert (carousel.path / "uploads" / "panorama.png").exists()

    list_page = client.get("/carousel")
    assert list_page.status_code == 200
    assert b"Room Launch" in list_page.data
    assert b"Delete" in list_page.data

    detail = client.get(f"/carousel/{carousel.path.name}")
    assert detail.status_code == 200
    assert b"room-launch-slide-02.png" in detail.data

    zip_response = client.get(f"/download/carousel/{carousel.path.name}/zip")
    assert zip_response.status_code == 200
    assert zip_response.headers["Content-Disposition"].startswith("attachment")

    delete = client.post(f"/carousel/{carousel.path.name}/delete", follow_redirects=True)
    assert delete.status_code == 200
    assert b"No saved carousels yet." in delete.data
    assert not carousel.path.exists()
