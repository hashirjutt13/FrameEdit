from __future__ import annotations

from PIL import Image, ImageDraw

from frameedit.config import TextConfig
from frameedit.image_ops import _text_lines, load_font


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
