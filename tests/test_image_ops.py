from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from frameedit.config import TextConfig
from frameedit import image_ops
from frameedit.image_ops import _text_lines, load_font, open_oriented_image


def test_last_word_second_line_forces_two_line_product_title() -> None:
    config = TextConfig(
        text="ECLAT CONSOLE",
        font=None,
        size=86,
        center=(540, 940),
        color="#f4efe6",
        auto_multiline=True,
        max_width=720,
        line_spacing=1.05,
        letter_spacing=150,
        last_word_second_line=True,
    )
    image = Image.new("RGBA", (1080, 1920))
    draw = ImageDraw.Draw(image)

    assert _text_lines(draw, config, load_font(config)) == ["ECLAT", "CONSOLE"]


def test_open_oriented_image_registers_heif_for_heic_suffix(monkeypatch, tmp_path) -> None:
    source = tmp_path / "source.heic"
    Image.new("RGB", (3, 4), "red").save(source, format="PNG")
    calls = 0

    def fake_register() -> bool:
        nonlocal calls
        calls += 1
        return True

    monkeypatch.setattr(image_ops, "register_heif_support", fake_register)

    image = open_oriented_image(source)

    assert image.size == (3, 4)
    assert calls == 1


def test_open_oriented_image_reports_missing_heif_dependency(monkeypatch, tmp_path) -> None:
    source = tmp_path / "source.heic"
    Image.new("RGB", (3, 4), "red").save(source, format="PNG")
    monkeypatch.setattr(image_ops, "register_heif_support", lambda: False)

    with pytest.raises(OSError, match="pillow-heif"):
        open_oriented_image(source)
