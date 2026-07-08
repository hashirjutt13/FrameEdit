"""Carousel panorama splitting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from frameedit.image_ops import fit_to_size, open_oriented_image, register_heif_support

from .generation import GeneratedFile
from .slugs import slugify


SUPPORTED_CAROUSEL_INPUT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MIN_SLIDES = 2
MAX_SLIDES = 20
SLIDE_FORMATS = {
    "portrait_3x4": {
        "label": "3:4 portrait",
        "slide_size": (1080, 1440),
        "aspect_ratio": "3:4",
    },
    "portrait_4x5": {
        "label": "4:5 portrait",
        "slide_size": (1080, 1350),
        "aspect_ratio": "4:5",
    },
    "square_1x1": {
        "label": "1:1 square",
        "slide_size": (1080, 1080),
        "aspect_ratio": "1:1",
    },
}


@dataclass(frozen=True)
class CarouselSlide:
    path: Path
    label: str
    slide_number: int
    upload_order: int


@dataclass(frozen=True)
class CarouselPanoramaResult:
    files: list[GeneratedFile]
    slides: list[CarouselSlide]
    source_size: tuple[int, int]
    slide_format: str
    format_label: str
    aspect_ratio: str
    slide_count: int
    slide_size: tuple[int, int]
    working_canvas_size: tuple[int, int]
    fit_mode: str


class CarouselPanoramaError(ValueError):
    """Raised when a carousel panorama request cannot be processed."""


def render_carousel_panorama(
    source: Path,
    *,
    output_dir: Path,
    carousel_name: str,
    slide_count: int = 3,
    slide_format: str = "portrait_3x4",
    fit_mode: str = "crop",
) -> CarouselPanoramaResult:
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_CAROUSEL_INPUT_EXTENSIONS:
        raise CarouselPanoramaError(f"Unsupported file type: {suffix or 'unknown'}.")
    if suffix in {".heic", ".heif"} and not register_heif_support():
        raise CarouselPanoramaError("HEIC/HEIF input found, but pillow-heif is not installed.")

    source_image = open_oriented_image(source)
    spec = _slide_spec(slide_format)
    slide_count = _validated_slide_count(slide_count)
    _validate_horizontal_source(source_image)
    slide_size = spec["slide_size"]
    working_canvas_size = (slide_size[0] * slide_count, slide_size[1])
    _validate_source_ratio(source_image.size, working_canvas_size, slide_count)
    canvas = _prepare_canvas(source_image, working_canvas_size, fit_mode)

    slide_dir = output_dir / "carousel_panorama"
    slide_dir.mkdir(parents=True, exist_ok=True)
    name_slug = slugify(carousel_name, fallback="carousel-panorama")
    slides: list[CarouselSlide] = []
    files: list[GeneratedFile] = []

    for index in range(slide_count):
        slide_number = index + 1
        left = index * slide_size[0]
        slide = canvas.crop((left, 0, left + slide_size[0], slide_size[1]))
        target = slide_dir / f"{name_slug}-slide-{slide_number:02d}.png"
        slide.save(target, format="PNG")

        label = f"Slide {slide_number:02d}"
        carousel_slide = CarouselSlide(
            path=target,
            label=label,
            slide_number=slide_number,
            upload_order=slide_number,
        )
        slides.append(carousel_slide)
        files.append(GeneratedFile(kind="carousel_panorama", path=target, label=label))

    return CarouselPanoramaResult(
        files=files,
        slides=slides,
        source_size=source_image.size,
        slide_format=slide_format,
        format_label=str(spec["label"]),
        aspect_ratio=str(spec["aspect_ratio"]),
        slide_count=slide_count,
        slide_size=slide_size,
        working_canvas_size=canvas.size,
        fit_mode=fit_mode,
    )


def _slide_spec(slide_format: str) -> dict[str, object]:
    try:
        return SLIDE_FORMATS[slide_format]
    except KeyError as exc:
        raise CarouselPanoramaError("Choose a supported slide format.") from exc


def _validated_slide_count(value: int) -> int:
    if value < MIN_SLIDES or value > MAX_SLIDES:
        raise CarouselPanoramaError(f"Slide count must be between {MIN_SLIDES} and {MAX_SLIDES}.")
    return value


def _validate_horizontal_source(image: Image.Image) -> None:
    width, height = image.size
    if width <= height:
        raise CarouselPanoramaError("Upload a horizontal source image for carousel panoramas.")


def _validate_source_ratio(
    source_size: tuple[int, int],
    expected_size: tuple[int, int],
    slide_count: int,
) -> None:
    source_width, source_height = source_size
    expected_width, expected_height = expected_size
    if source_width * expected_height == source_height * expected_width:
        return
    expected_ratio = _simplified_ratio(expected_size)
    source_ratio = _simplified_ratio(source_size)
    raise CarouselPanoramaError(
        "Source image ratio must match the recommended "
        f"{expected_ratio} canvas for {slide_count} slides "
        f"({expected_width} x {expected_height}). "
        f"Uploaded source is {source_width} x {source_height}, ratio {source_ratio}."
    )


def _simplified_ratio(size: tuple[int, int]) -> str:
    width, height = size
    divisor = _greatest_common_divisor(width, height)
    return f"{width // divisor}:{height // divisor}"


def _greatest_common_divisor(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return max(left, 1)


def _prepare_canvas(
    image: Image.Image,
    size: tuple[int, int],
    fit_mode: str,
) -> Image.Image:
    if fit_mode == "crop":
        return fit_to_size(image, size)
    if fit_mode == "stretch":
        return image.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    raise CarouselPanoramaError("Choose a supported source fit mode.")
