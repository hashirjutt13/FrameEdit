from __future__ import annotations

from io import BytesIO
from pathlib import Path

import yaml
from PIL import Image, ImageDraw


def image_upload(name: str, size: tuple[int, int], color: str = "red") -> tuple[BytesIO, str]:
    handle = BytesIO()
    Image.new("RGB", size, color).save(handle, format="PNG")
    handle.seek(0)
    return handle, name


def write_test_preset(root: Path, slug: str = "test-brand") -> Path:
    assets = root / "assets"
    vignettes = assets / "vignettes"
    vignettes.mkdir(parents=True)
    for name in ["centered", "top", "bottom"]:
        vignette = Image.new("RGBA", (1080, 1440), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        draw.rectangle([0, 0, 1080, 120], fill=(0, 0, 0, 100))
        vignette.save(vignettes / f"{name}.png")

    Image.new("RGBA", (1080, 1920), (0, 0, 0, 255)).save(assets / "black.png")
    logo = Image.new("RGBA", (300, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    draw.rectangle([20, 20, 280, 100], fill=(255, 255, 255, 220))
    logo.save(assets / "logo.png")

    presets = root / "presets"
    presets.mkdir(parents=True)
    preset_path = presets / f"{slug}.yaml"
    preset_path.write_text(
        yaml.safe_dump(
            {
                "brand": {"name": "Test Brand", "slug": slug},
                "input_dir": "../input",
                "output_dir": "../output",
                "scan_recursive": False,
                "aspect_ratio_tolerance": 0.02,
                "overwrite": True,
                "supported_extensions": [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"],
                "post": {
                    "size": [1080, 1440],
                    "default_vignette": "centered",
                    "vignette_opacity": 1.0,
                    "vignettes": {
                        "centered": "../assets/vignettes/centered.png",
                        "top": "../assets/vignettes/top.png",
                        "bottom": "../assets/vignettes/bottom.png",
                    },
                    "logo": {
                        "file": "../assets/logo.png",
                        "scale": 0.2,
                        "center": [540, 100],
                        "opacity": 1.0,
                    },
                },
                "webp_variant": {
                    "enabled": True,
                    "include_logo": True,
                    "lossless": True,
                    "quality": 100,
                    "method": 6,
                },
                "reel_cover": {
                    "size": [1080, 1920],
                    "background_blur": {"enabled": False, "intensity": 0, "max_radius": 100},
                    "black_overlay": {"file": "../assets/black.png", "opacity": 0.6},
                    "logo": {
                        "file": "../assets/logo.png",
                        "scale": 0.2,
                        "center": [540, 360],
                        "opacity": 1.0,
                    },
                    "product_name": {
                        "text": "ECLAT CONSOLE",
                        "font": "",
                        "size": 92,
                        "center": [540, 940],
                        "color": "#f4efe6",
                        "auto_multiline": True,
                        "max_width": 720,
                        "line_spacing": 1.05,
                        "letter_spacing": 0,
                        "last_word_second_line": False,
                    },
                    "category_name": {
                        "text": "Consoles",
                        "font": "",
                        "size": 82,
                        "center": [540, 1580],
                        "color": "#f4efe6",
                        "auto_multiline": False,
                        "max_width": None,
                        "line_spacing": 1.05,
                        "letter_spacing": 0,
                        "last_word_second_line": False,
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return preset_path
