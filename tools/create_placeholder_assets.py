"""Create replaceable starter assets for local development."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def main() -> None:
    (ASSETS / "vignettes").mkdir(parents=True, exist_ok=True)
    _save_centered_vignette(ASSETS / "vignettes" / "centered.png", (1080, 1440))
    _save_directional_vignette(ASSETS / "vignettes" / "top.png", (1080, 1440), edge="top")
    _save_directional_vignette(ASSETS / "vignettes" / "bottom.png", (1080, 1440), edge="bottom")
    _save_black_overlay(ASSETS / "black_9x16.png", (1080, 1920))
    _save_logo_placeholder(ASSETS / "logo-placeholder.png", (900, 300))


def _save_centered_vignette(path: Path, size: tuple[int, int]) -> None:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = image.load()
    center_x = width / 2
    center_y = height / 2
    max_distance = ((center_x**2) + (center_y**2)) ** 0.5

    for y in range(height):
        for x in range(width):
            dx = x - center_x
            dy = y - center_y
            distance = ((dx * dx) + (dy * dy)) ** 0.5 / max_distance
            alpha = int(max(0.0, min(1.0, (distance - 0.42) / 0.58)) ** 1.9 * 185)
            pixels[x, y] = (0, 0, 0, alpha)

    image.save(path)


def _save_directional_vignette(path: Path, size: tuple[int, int], *, edge: str) -> None:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = image.load()

    for y in range(height):
        t = y / max(1, height - 1)
        if edge == "top":
            strength = max(0.0, 1.0 - t * 1.7)
        else:
            strength = max(0.0, (t - 0.35) / 0.65)
        alpha = int((strength**1.6) * 190)
        for x in range(width):
            pixels[x, y] = (0, 0, 0, alpha)

    image.save(path)


def _save_black_overlay(path: Path, size: tuple[int, int]) -> None:
    Image.new("RGBA", size, (0, 0, 0, 255)).save(path)


def _save_logo_placeholder(path: Path, size: tuple[int, int]) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _font(112)
    text = "LOGO"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    center = (size[0] // 2, size[1] // 2)
    padding_x = 78
    padding_y = 38
    box = [
        center[0] - text_width // 2 - padding_x,
        center[1] - text_height // 2 - padding_y,
        center[0] + text_width // 2 + padding_x,
        center[1] + text_height // 2 + padding_y,
    ]
    draw.rounded_rectangle(box, radius=18, outline=(255, 255, 255, 210), width=8)
    draw.text(
        (center[0] - text_width / 2, center[1] - text_height / 2 - bbox[1]),
        text,
        fill=(255, 255, 255, 235),
        font=font,
    )
    image.save(path)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)

    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


if __name__ == "__main__":
    main()

