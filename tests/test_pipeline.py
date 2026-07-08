from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from frameedit.config import load_config
from frameedit.pipeline import AssetType, classify_image, run_batch


def test_classify_supported_ratios(tmp_path: Path) -> None:
    post = tmp_path / "post.jpg"
    reel = tmp_path / "reel.jpg"
    square = tmp_path / "square.jpg"
    Image.new("RGB", (750, 1000), "red").save(post)
    Image.new("RGB", (900, 1600), "blue").save(reel)
    Image.new("RGB", (1000, 1000), "green").save(square)

    assert classify_image(post, 0.02).asset_type == AssetType.POST
    assert classify_image(reel, 0.02).asset_type == AssetType.REEL
    assert classify_image(square, 0.02).asset_type == AssetType.UNSUPPORTED


def test_end_to_end_generation(tmp_path: Path) -> None:
    _write_assets(tmp_path)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    Image.new("RGB", (750, 1000), (200, 80, 60)).save(input_dir / "chair.jpg")
    Image.new("RGB", (900, 1600), (40, 80, 160)).save(input_dir / "reel.jpg")

    config = load_config(_write_config(tmp_path))
    result = run_batch(config)

    post_png = tmp_path / "output" / "posts_instagram" / "chair.png"
    post_webp = tmp_path / "output" / "posts_webp_no_vignette" / "chair.webp"
    reel = tmp_path / "output" / "reel_cover" / "reel-cover.png"

    assert [output.target for output in result.outputs] == [post_png, post_webp, reel]
    assert Image.open(post_png).size == (1080, 1440)
    assert Image.open(post_webp).size == (1080, 1440)
    assert Image.open(reel).size == (1080, 1920)

    post_corner = Image.open(post_png).convert("RGBA").getpixel((10, 10))
    webp_corner = Image.open(post_webp).convert("RGBA").getpixel((10, 10))
    assert post_corner[0] < webp_corner[0]


def test_dry_run_writes_nothing_and_warns_for_multiple_reels(tmp_path: Path) -> None:
    _write_assets(tmp_path)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    Image.new("RGB", (900, 1600), "blue").save(input_dir / "reel-a.jpg")
    Image.new("RGB", (900, 1600), "purple").save(input_dir / "reel-b.jpg")

    config = load_config(_write_config(tmp_path))
    result = run_batch(config, dry_run=True)

    assert not (tmp_path / "output").exists()
    assert any("More than one 9:16" in warning for warning in result.warnings)
    assert result.outputs[0].target == tmp_path / "output" / "reel_cover" / "reel-cover.png"


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
input_dir: input
output_dir: output
post:
  size: [1080, 1440]
  default_vignette: centered
  vignette_opacity: 1.0
  vignettes:
    centered: assets/vignettes/centered.png
    top: assets/vignettes/top.png
    bottom: assets/vignettes/bottom.png
  logo:
    file: assets/logo.png
    scale: 0.2
    center: [540, 100]
    opacity: 1.0
webp_variant:
  enabled: true
  include_logo: true
  lossless: true
  quality: 100
  method: 6
reel_cover:
  size: [1080, 1920]
  black_overlay:
    file: assets/black.png
    opacity: 0.6
  logo:
    file: assets/logo.png
    scale: 0.2
    center: [540, 360]
    opacity: 1.0
  product_name:
    text: ECLAT CONSOLE
    font:
    size: 92
    center: [540, 940]
    color: "#f4efe6"
    auto_multiline: true
    max_width: 720
    line_spacing: 1.05
  category_name:
    text: Consoles
    font:
    size: 82
    center: [540, 1580]
    color: "#f4efe6"
""",
        encoding="utf-8",
    )
    return config_path


def _write_assets(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    vignettes = assets / "vignettes"
    vignettes.mkdir(parents=True)

    for name in ["centered", "top", "bottom"]:
        vignette = Image.new("RGBA", (1080, 1440), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        draw.rectangle([0, 0, 1080, 120], fill=(0, 0, 0, 120))
        draw.rectangle([0, 1320, 1080, 1440], fill=(0, 0, 0, 120))
        vignette.save(vignettes / f"{name}.png")

    Image.new("RGBA", (1080, 1920), (0, 0, 0, 255)).save(assets / "black.png")
    logo = Image.new("RGBA", (400, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    draw.rectangle([20, 20, 380, 140], fill=(255, 255, 255, 200))
    logo.save(assets / "logo.png")

