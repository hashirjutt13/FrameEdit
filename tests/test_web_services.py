from __future__ import annotations

import yaml
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw

from frameedit.web_services.assets import AssetError, list_assets, save_asset_upload, seed_local_assets
from frameedit.web_services.carousel_panorama import CarouselPanoramaError, render_carousel_panorama
from frameedit.web_services.grid_mosaic import render_grid_mosaic
from frameedit.web_services.presets import create_preset, import_preset_json, list_presets, load_preset
from frameedit.web_services.projects import (
    ProjectGridError,
    create_project_dir,
    default_grid_layout,
    list_projects,
    project_grid_candidates,
    project_grid_layout,
    save_project_grid_layout,
    write_project_metadata,
)
from frameedit.web_services.slugs import safe_filename, slugify
from frameedit.web_services.zipfiles import create_output_zip

from web_helpers import write_test_preset


class DummyUpload:
    def __init__(self, filename: str, payload: bytes = b"data") -> None:
        self.filename = filename
        self.stream = BytesIO(payload)


def test_slug_and_safe_filename() -> None:
    assert slugify("ECLAT CONSOLE") == "eclat-console"
    assert safe_filename("../../Logo File.PNG") == "logo-file.png"


def test_preset_load_and_create(tmp_path: Path) -> None:
    root = tmp_path / "data"
    write_test_preset(root)

    preset = load_preset("test-brand", root)
    assert preset.name == "Test Brand"
    assert preset.config.post.size == (1080, 1440)

    created = create_preset("Another Brand", root)
    assert created.slug == "another-brand"
    assert {item.slug for item in list_presets(root)} == {
        "test-brand",
        "another-brand",
        "starter-brand",
    }


def test_import_preset_json_creates_and_updates_presets(tmp_path: Path) -> None:
    root = tmp_path / "data"
    source_path = write_test_preset(root)
    raw = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    raw["brand"] = {"name": "Imported Brand", "slug": "imported-brand"}
    raw["post"]["logo"]["scale"] = 0.33

    imported = import_preset_json({"settings": raw}, root)

    assert imported.slug == "imported-brand"
    assert imported.name == "Imported Brand"
    assert imported.config.post.logo.scale == 0.33

    raw["brand"] = {"name": "Updated Test Brand", "slug": "ignored-brand"}
    raw["post"]["logo"]["scale"] = 0.44
    updated = import_preset_json(raw, root, target_slug="test-brand")

    assert updated.slug == "test-brand"
    assert updated.name == "Updated Test Brand"
    assert load_preset("test-brand", root).config.post.logo.scale == 0.44


def test_asset_upload_validation_and_listing(tmp_path: Path) -> None:
    root = tmp_path / "data"
    saved = save_asset_upload(DummyUpload("../../Logo.PNG", b"png"), "logos", root)
    assert saved.name == "logo.png"
    assert list_assets("logos", root)[0].name == "logo.png"

    try:
        save_asset_upload(DummyUpload("font.exe"), "fonts", root)
    except AssetError as exc:
        assert ".otf" in str(exc)
    else:
        raise AssertionError("Expected AssetError")


def test_seed_local_assets_imports_logo_and_font_files(tmp_path: Path) -> None:
    root = tmp_path / "data"
    source = tmp_path / "source"
    (source / "brand").mkdir(parents=True)
    (source / "logos").mkdir(parents=True)
    (source / "assets" / "fonts").mkdir(parents=True)
    (source / "output").mkdir()
    (source / "brand" / "main-logo.svg").write_text("<svg></svg>", encoding="utf-8")
    (source / "logos" / "brand-mark.png").write_bytes(b"png")
    (source / "assets" / "fonts" / "display.otf").write_bytes(b"font")
    (source / "output" / "ignored-logo.png").write_bytes(b"ignored")

    result = seed_local_assets(root, source_root=source)

    assert {record.name for record in result.imported} == {
        "brand-mark.png",
        "display.otf",
        "main-logo.svg",
    }
    assert (root / "assets" / "logos" / "main-logo.svg").exists()
    assert (root / "assets" / "logos" / "brand-mark.png").exists()
    assert (root / "assets" / "fonts" / "display.otf").exists()
    assert not (root / "assets" / "logos" / "ignored-logo.png").exists()

    again = seed_local_assets(root, source_root=source)
    assert not again.imported
    assert {record.name for record in again.skipped} == {
        "brand-mark.png",
        "display.otf",
        "main-logo.svg",
    }


def test_project_metadata_and_zip(tmp_path: Path) -> None:
    root = tmp_path / "data"
    project_path = create_project_dir(
        brand_name="Test Brand",
        brand_slug="test-brand",
        product_name="ECLAT CONSOLE",
        root=root,
    )
    output = project_path / "posts_instagram" / "eclat-console-post-01.png"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"fake")
    zip_path = create_output_zip(
        project_path,
        zip_path=project_path / "eclat-console-test-brand.zip",
        archive_root="eclat-console-test-brand",
    )
    record = write_project_metadata(
        project_path,
        brand_name="Test Brand",
        brand_slug="test-brand",
        product_name="ECLAT CONSOLE",
        zip_path=zip_path,
        outputs=[output],
    )

    assert record.product_slug == "eclat-console"
    assert list_projects(root=root, query="eclat")[0].path == project_path
    with ZipFile(zip_path) as archive:
        assert "eclat-console-test-brand/posts_instagram/eclat-console-post-01.png" in archive.namelist()


def test_grid_mosaic_split_bleed_and_zip(tmp_path: Path) -> None:
    profile_source = tmp_path / "profile-source.png"
    profile = Image.new("RGB", (3240, 1440), "white")
    draw = ImageDraw.Draw(profile)
    draw.rectangle([0, 0, 1079, 1439], fill=(255, 0, 0))
    draw.rectangle([1080, 0, 2159, 1439], fill=(0, 255, 0))
    draw.rectangle([2160, 0, 3239, 1439], fill=(0, 0, 255))
    profile.save(profile_source)

    profile_result = render_grid_mosaic(
        profile_source,
        output_dir=tmp_path / "profile-outputs",
        mosaic_name="Profile Room Launch",
    )

    assert profile_result.tile_format == "profile_3x4"
    assert profile_result.source_mode == "profile"
    assert profile_result.working_canvas_size == (3240, 1440)
    assert profile_result.visible_tile_size == (1080, 1440)
    assert profile_result.output_tile_size == (1080, 1440)
    assert profile_result.left_bleed == 0
    assert profile_result.right_bleed == 0
    profile_first = Image.open(profile_result.tiles[0].path).convert("RGB")
    profile_middle = Image.open(profile_result.tiles[1].path).convert("RGB")
    profile_third = Image.open(profile_result.tiles[2].path).convert("RGB")
    assert profile_first.size == (1080, 1440)
    assert profile_first.getpixel((540, 10)) == (255, 0, 0)
    assert profile_middle.getpixel((540, 10)) == (0, 255, 0)
    assert profile_third.getpixel((540, 10)) == (0, 0, 255)

    source = tmp_path / "source.png"
    image = Image.new("RGB", (3106, 1350), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 32, 1349], fill=(10, 20, 30))
    draw.rectangle([33, 0, 1045, 1349], fill=(255, 0, 0))
    draw.rectangle([1046, 0, 2058, 1349], fill=(0, 255, 0))
    draw.rectangle([2059, 0, 3071, 1349], fill=(0, 0, 255))
    draw.rectangle([3072, 0, 3105, 1349], fill=(30, 20, 10))
    image.save(source)

    result = render_grid_mosaic(
        source,
        output_dir=tmp_path / "outputs",
        mosaic_name="Room Launch",
        tile_format="feed_4x5",
    )

    assert result.tile_format == "feed_4x5"
    assert result.source_mode == "bleed"
    assert result.working_canvas_size == (3106, 1350)
    assert result.visible_tile_size == (1013, 1350)
    assert result.visible_canvas_size == (
        result.visible_tile_size[0] * 3,
        result.visible_tile_size[1],
    )
    assert result.output_tile_size == (1080, 1350)
    assert result.left_bleed == 33
    assert result.right_bleed == 34
    assert len(result.tiles) == 3
    assert result.tiles[0].path.name == "room-launch-upload-03-col-01.png"
    assert result.upload_tiles[0].path.name == "room-launch-upload-01-col-03.png"

    first = Image.open(result.tiles[0].path).convert("RGB")
    middle = Image.open(result.tiles[1].path).convert("RGB")
    third = Image.open(result.tiles[2].path).convert("RGB")
    assert first.size == (1080, 1350)
    assert first.getpixel((10, 10)) == (10, 20, 30)
    assert first.getpixel((40, 10)) == (255, 0, 0)
    assert first.getpixel((1050, 10)) == (0, 255, 0)
    assert middle.getpixel((10, 10)) == (255, 0, 0)
    assert middle.getpixel((540, 10)) == (0, 255, 0)
    assert middle.getpixel((1050, 10)) == (0, 0, 255)
    assert third.getpixel((10, 10)) == (0, 255, 0)
    assert third.getpixel((540, 10)) == (0, 0, 255)
    assert third.getpixel((1070, 10)) == (30, 20, 10)

    zip_path = create_output_zip(
        tmp_path / "outputs",
        zip_path=tmp_path / "outputs" / "room-launch.zip",
        archive_root="room-launch",
    )
    with ZipFile(zip_path) as archive:
        assert "room-launch/grid_mosaic/room-launch-upload-01-col-03.png" in archive.namelist()


def test_carousel_panorama_split_and_zip(tmp_path: Path) -> None:
    source = tmp_path / "carousel-source.png"
    image = Image.new("RGB", (3240, 1440), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 1079, 1439], fill=(255, 0, 0))
    draw.rectangle([1080, 0, 2159, 1439], fill=(0, 255, 0))
    draw.rectangle([2160, 0, 3239, 1439], fill=(0, 0, 255))
    image.save(source)

    result = render_carousel_panorama(
        source,
        output_dir=tmp_path / "carousel-outputs",
        carousel_name="Room Launch",
        slide_count=3,
    )

    assert result.slide_format == "portrait_3x4"
    assert result.slide_count == 3
    assert result.working_canvas_size == (3240, 1440)
    assert result.slide_size == (1080, 1440)
    assert [slide.path.name for slide in result.slides] == [
        "room-launch-slide-01.png",
        "room-launch-slide-02.png",
        "room-launch-slide-03.png",
    ]
    first = Image.open(result.slides[0].path).convert("RGB")
    middle = Image.open(result.slides[1].path).convert("RGB")
    third = Image.open(result.slides[2].path).convert("RGB")
    assert first.size == (1080, 1440)
    assert first.getpixel((540, 10)) == (255, 0, 0)
    assert middle.getpixel((540, 10)) == (0, 255, 0)
    assert third.getpixel((540, 10)) == (0, 0, 255)

    zip_path = create_output_zip(
        tmp_path / "carousel-outputs",
        zip_path=tmp_path / "carousel-outputs" / "room-launch.zip",
        archive_root="room-launch",
    )
    with ZipFile(zip_path) as archive:
        assert "room-launch/carousel_panorama/room-launch-slide-01.png" in archive.namelist()

    for slide_format, source_size, expected_size in [
        ("portrait_4x5", (2160, 1350), (1080, 1350)),
        ("square_1x1", (2160, 1080), (1080, 1080)),
    ]:
        alternate_source = tmp_path / f"{slide_format}-source.png"
        Image.new("RGB", source_size, "white").save(alternate_source)
        alternate = render_carousel_panorama(
            alternate_source,
            output_dir=tmp_path / f"{slide_format}-outputs",
            carousel_name=slide_format,
            slide_count=2,
            slide_format=slide_format,
        )
        assert alternate.slide_size == expected_size
        assert alternate.working_canvas_size == (expected_size[0] * 2, expected_size[1])
        assert Image.open(alternate.slides[0].path).size == expected_size

    try:
        render_carousel_panorama(
            source,
            output_dir=tmp_path / "too-many-outputs",
            carousel_name="Too Many",
            slide_count=21,
        )
    except CarouselPanoramaError as exc:
        assert "between 2 and 20" in str(exc)
    else:
        raise AssertionError("Expected CarouselPanoramaError")

    wrong_ratio_source = tmp_path / "wrong-ratio-source.png"
    Image.new("RGB", (1920, 1080), "red").save(wrong_ratio_source)
    try:
        render_carousel_panorama(
            wrong_ratio_source,
            output_dir=tmp_path / "wrong-ratio-outputs",
            carousel_name="Wrong Ratio",
        )
    except CarouselPanoramaError as exc:
        assert "must match the recommended 9:4 canvas" in str(exc)
        assert "ratio 16:9" in str(exc)
    else:
        raise AssertionError("Expected CarouselPanoramaError")

    vertical_source = tmp_path / "vertical-source.png"
    Image.new("RGB", (1080, 1440), "red").save(vertical_source)
    try:
        render_carousel_panorama(
            vertical_source,
            output_dir=tmp_path / "vertical-outputs",
            carousel_name="Vertical",
        )
    except CarouselPanoramaError as exc:
        assert "horizontal source image" in str(exc)
    else:
        raise AssertionError("Expected CarouselPanoramaError")


def test_project_grid_candidates_default_layout_and_saved_layout(tmp_path: Path) -> None:
    root = tmp_path / "data"
    project_path = create_project_dir(
        brand_name="Test Brand",
        brand_slug="test-brand",
        product_name="ECLAT CONSOLE",
        root=root,
    )
    outputs = [
        project_path / "posts_instagram" / "eclat-console-post-01.png",
        project_path / "posts_webp_no_vignette" / "eclat-console-post-01.webp",
        project_path / "posts_instagram" / "eclat-console-post-02.png",
        project_path / "reel_cover" / "eclat-console-reel-cover.png",
    ]
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake")
    record = write_project_metadata(
        project_path,
        brand_name="Test Brand",
        brand_slug="test-brand",
        product_name="ECLAT CONSOLE",
        zip_path=None,
        outputs=outputs,
    )

    candidates = project_grid_candidates(record)
    assert [candidate.relative_path for candidate in candidates] == [
        "posts_instagram/eclat-console-post-01.png",
        "posts_instagram/eclat-console-post-02.png",
        "reel_cover/eclat-console-reel-cover.png",
    ]
    assert [candidate.kind for candidate in candidates] == ["post", "post", "reel"]
    assert default_grid_layout(record) == [
        "posts_instagram/eclat-console-post-01.png",
        "reel_cover/eclat-console-reel-cover.png",
        "posts_instagram/eclat-console-post-02.png",
    ]

    saved = save_project_grid_layout(
        project_path,
        [
            "reel_cover/eclat-console-reel-cover.png",
            "posts_instagram/eclat-console-post-01.png",
            "posts_instagram/eclat-console-post-02.png",
        ],
    )
    assert project_grid_layout(saved) == [
        "reel_cover/eclat-console-reel-cover.png",
        "posts_instagram/eclat-console-post-01.png",
        "posts_instagram/eclat-console-post-02.png",
    ]

    try:
        save_project_grid_layout(
            project_path,
            [
                "reel_cover/eclat-console-reel-cover.png",
                "../outside.png",
                "posts_instagram/eclat-console-post-02.png",
            ],
        )
    except ProjectGridError as exc:
        assert "unknown project file" in str(exc)
    else:
        raise AssertionError("Expected ProjectGridError")
