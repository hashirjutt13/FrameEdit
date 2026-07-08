from __future__ import annotations

from pathlib import Path

import pytest

from frameedit.config import ConfigError, load_config


def test_load_config_resolves_relative_paths(tmp_path: Path) -> None:
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
  background_blur:
    enabled: true
    intensity: 0.15
    max_radius: 100
  black_overlay:
    file: assets/black.png
    opacity: 0.6
  logo:
    file: assets/logo.png
    scale: 0.2
    center: [540, 360]
    opacity: 1.0
  product_name:
    text: Test Product
    font:
    size: 92
    center: [540, 940]
    color: "#ffffff"
    auto_multiline: true
    max_width: 720
    line_spacing: 1.05
    letter_spacing: 150
    last_word_second_line: true
  category_name:
    text: Category
    font:
    size: 82
    center: [540, 1580]
    color: "#ffffff"
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.input_dir == tmp_path / "input"
    assert config.output_dir == tmp_path / "output"
    assert config.post.logo.file == tmp_path / "assets" / "logo.png"
    assert config.reel_cover.background_blur.enabled is True
    assert config.reel_cover.background_blur.intensity == 0.15
    assert config.reel_cover.background_blur.radius == 15
    assert config.reel_cover.product_name.font is None
    assert config.reel_cover.product_name.letter_spacing == 150
    assert config.reel_cover.product_name.last_word_second_line is True


def test_default_vignette_must_exist_in_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
input_dir: input
output_dir: output
post:
  size: [1080, 1440]
  default_vignette: missing
  vignette_opacity: 1.0
  vignettes:
    centered: assets/vignettes/centered.png
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
    text: Test Product
    font:
    size: 92
    center: [540, 940]
    color: "#ffffff"
  category_name:
    text: Category
    font:
    size: 82
    center: [540, 1580]
    color: "#ffffff"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="default_vignette"):
        load_config(config_path)
