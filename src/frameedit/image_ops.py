"""Image loading, compositing, and text rendering helpers."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

from .config import LogoConfig, TextConfig


def register_heif_support() -> bool:
    """Register HEIF/HEIC support when pillow-heif is installed."""

    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        return False

    register_heif_opener()
    return True


def open_oriented_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGBA")


def fit_to_size(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(
        image.convert("RGBA"),
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def open_layer(path: Path, expected_size: tuple[int, int] | None = None) -> Image.Image:
    with Image.open(path) as image:
        layer = ImageOps.exif_transpose(image).convert("RGBA")

    if expected_size is not None and layer.size != expected_size:
        raise ValueError(f"{path} is {layer.size[0]}x{layer.size[1]}, expected {expected_size[0]}x{expected_size[1]}.")
    return layer


def with_opacity(layer: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 1.0:
        return layer.convert("RGBA")

    result = layer.convert("RGBA").copy()
    alpha = result.getchannel("A").point(lambda pixel: round(pixel * opacity))
    result.putalpha(alpha)
    return result


def composite_center(base: Image.Image, layer: Image.Image, center: tuple[int, int]) -> Image.Image:
    result = base.convert("RGBA").copy()
    x = round(center[0] - layer.width / 2)
    y = round(center[1] - layer.height / 2)
    result.alpha_composite(layer.convert("RGBA"), (x, y))
    return result


def scale_logo(logo: Image.Image, config: LogoConfig, target_size: tuple[int, int]) -> Image.Image:
    target_width = max(1, round(target_size[0] * config.scale))
    ratio = target_width / logo.width
    target_height = max(1, round(logo.height * ratio))
    resized = logo.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return with_opacity(resized, config.opacity)


def parse_color(color: str) -> tuple[int, int, int, int]:
    try:
        rgba = ImageColor.getcolor(color, "RGBA")
    except ValueError as exc:
        raise ValueError(f"Invalid color value: {color}") from exc
    return rgba


def load_font(config: TextConfig) -> ImageFont.ImageFont:
    if config.font is not None:
        return ImageFont.truetype(str(config.font), config.size)

    try:
        return ImageFont.load_default(size=config.size)
    except TypeError:
        return ImageFont.load_default()


def draw_centered_text_block(image: Image.Image, config: TextConfig) -> Image.Image:
    result = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(result)
    font = load_font(config)
    color = parse_color(config.color)
    tracking = _tracking_px(config)
    lines = _text_lines(draw, config, font)
    if not lines:
        return result

    spacing = _line_spacing_px(draw, font, config)
    block_width, block_height = _block_size(draw, lines, font, spacing, tracking)
    y = round(config.center[1] - block_height / 2)

    cursor_y = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = _text_width(draw, line, font, tracking)
        line_height = bbox[3] - bbox[1]
        _draw_text_with_tracking(
            draw,
            (round(config.center[0] - line_width / 2), cursor_y - bbox[1]),
            line,
            font,
            color,
            tracking,
        )
        cursor_y += line_height + spacing
    return result


def _text_lines(draw: ImageDraw.ImageDraw, config: TextConfig, font: ImageFont.ImageFont) -> list[str]:
    text = " ".join(config.text.split())
    if not text:
        return []

    if config.last_word_second_line:
        words = text.split(" ")
        if len(words) > 1:
            return [" ".join(words[:-1]), words[-1]]
        return [text]

    if not config.auto_multiline or not config.max_width:
        return [text]

    tracking = _tracking_px(config)
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = word if not current else f"{current} {word}"
        if _text_width(draw, candidate, font, tracking) <= config.max_width or not current:
            current = candidate
            continue
        lines.append(current)
        current = word

    if current:
        lines.append(current)
    return lines


def _tracking_px(config: TextConfig) -> float:
    return config.size * config.letter_spacing / 1000


def _text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    tracking: float,
) -> float:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    return width + max(0, len(text) - 1) * tracking


def _draw_text_with_tracking(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    color: tuple[int, int, int, int],
    tracking: float,
) -> None:
    x, y = position
    for index, char in enumerate(text):
        draw.text((x, y), char, fill=color, font=font)
        x += draw.textlength(char, font=font)
        if index < len(text) - 1:
            x += tracking


def _line_spacing_px(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    config: TextConfig,
) -> int:
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = max(1, bbox[3] - bbox[1])
    return round(line_height * max(0.0, config.line_spacing - 1.0))


def _block_size(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    spacing: int,
    tracking: float,
) -> tuple[float, int]:
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(_text_width(draw, line, font, tracking))
        heights.append(bbox[3] - bbox[1])
    return max(widths), sum(heights) + spacing * max(0, len(lines) - 1)
