"""Profile-grid mosaic splitting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from frameedit.image_ops import fit_to_size, open_oriented_image, register_heif_support

from .generation import GeneratedFile
from .slugs import slugify


SUPPORTED_MOSAIC_INPUT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
FEED_VISIBLE_TILE_SIZE = (1013, 1350)
FEED_BLEED_CANVAS_SIZE = (3106, 1350)
FEED_DISPLAY_CANVAS_SIZE = (FEED_VISIBLE_TILE_SIZE[0] * 3, FEED_VISIBLE_TILE_SIZE[1])
FEED_OUTPUT_TILE_SIZE = (1080, 1350)
FEED_LEFT_BLEED = 33
FEED_RIGHT_BLEED = 34
PROFILE_CANVAS_SIZE = (3240, 1440)
PROFILE_TILE_SIZE = (1080, 1440)
PROFILE_OUTPUT_TILE_SIZE = (1080, 1440)


@dataclass(frozen=True)
class MosaicTile:
    path: Path
    label: str
    column: int
    display_order: int
    upload_order: int


@dataclass(frozen=True)
class GridMosaicResult:
    files: list[GeneratedFile]
    tiles: list[MosaicTile]
    source_size: tuple[int, int]
    tile_format: str
    source_mode: str
    working_canvas_size: tuple[int, int]
    visible_canvas_size: tuple[int, int]
    visible_tile_size: tuple[int, int]
    output_tile_size: tuple[int, int]
    left_bleed: int
    right_bleed: int
    fit_mode: str

    @property
    def upload_tiles(self) -> list[MosaicTile]:
        return sorted(self.tiles, key=lambda tile: tile.upload_order)


class GridMosaicError(ValueError):
    """Raised when a mosaic request cannot be processed."""


def render_grid_mosaic(
    source: Path,
    *,
    output_dir: Path,
    mosaic_name: str,
    tile_format: str = "profile_3x4",
    source_mode: str = "bleed",
    fit_mode: str = "crop",
) -> GridMosaicResult:
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_MOSAIC_INPUT_EXTENSIONS:
        raise GridMosaicError(f"Unsupported file type: {suffix or 'unknown'}.")
    if suffix in {".heic", ".heif"} and not register_heif_support():
        raise GridMosaicError("HEIC/HEIF input found, but pillow-heif is not installed.")

    source_image = open_oriented_image(source)
    spec = _mosaic_spec(tile_format, source_mode)
    canvas = _prepare_canvas(source_image, spec["working_canvas_size"], fit_mode)

    tile_dir = output_dir / "grid_mosaic"
    tile_dir.mkdir(parents=True, exist_ok=True)
    name_slug = slugify(mosaic_name, fallback="grid-mosaic")
    tiles: list[MosaicTile] = []
    files: list[GeneratedFile] = []

    for column_index in range(3):
        column = column_index + 1
        upload_order = 4 - column
        tile = _compose_tile(canvas, column_index, spec=spec)
        target = tile_dir / f"{name_slug}-upload-{upload_order:02d}-col-{column:02d}.png"
        tile.save(target, format="PNG")

        label = f"Upload {upload_order:02d} · Column {column}"
        mosaic_tile = MosaicTile(
            path=target,
            label=label,
            column=column,
            display_order=column,
            upload_order=upload_order,
        )
        tiles.append(mosaic_tile)
        files.append(GeneratedFile(kind="grid_mosaic", path=target, label=label))

    return GridMosaicResult(
        files=files,
        tiles=tiles,
        source_size=source_image.size,
        tile_format=tile_format,
        source_mode=str(spec["source_mode"]),
        working_canvas_size=canvas.size,
        visible_canvas_size=spec["visible_canvas_size"],
        visible_tile_size=spec["visible_tile_size"],
        output_tile_size=spec["output_tile_size"],
        left_bleed=spec["left_bleed"],
        right_bleed=spec["right_bleed"],
        fit_mode=fit_mode,
    )


def _mosaic_spec(tile_format: str, source_mode: str) -> dict[str, object]:
    if tile_format == "profile_3x4":
        return {
            "source_mode": "profile",
            "working_canvas_size": PROFILE_CANVAS_SIZE,
            "visible_canvas_size": PROFILE_CANVAS_SIZE,
            "visible_tile_size": PROFILE_TILE_SIZE,
            "output_tile_size": PROFILE_OUTPUT_TILE_SIZE,
            "left_bleed": 0,
            "right_bleed": 0,
            "source_offset": 0,
        }

    if tile_format != "feed_4x5":
        raise GridMosaicError("Choose a supported tile format.")

    if source_mode == "bleed":
        return {
            "source_mode": "bleed",
            "working_canvas_size": FEED_BLEED_CANVAS_SIZE,
            "visible_canvas_size": FEED_DISPLAY_CANVAS_SIZE,
            "visible_tile_size": FEED_VISIBLE_TILE_SIZE,
            "output_tile_size": FEED_OUTPUT_TILE_SIZE,
            "left_bleed": FEED_LEFT_BLEED,
            "right_bleed": FEED_RIGHT_BLEED,
            "source_offset": 0,
        }
    raise GridMosaicError("Choose a supported source mode.")


def _prepare_canvas(
    image: Image.Image,
    size: tuple[int, int],
    fit_mode: str,
) -> Image.Image:

    if fit_mode == "crop":
        return fit_to_size(image, size)
    if fit_mode == "stretch":
        return image.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    raise GridMosaicError("Choose a supported source fit mode.")


def _compose_tile(
    canvas: Image.Image,
    column_index: int,
    *,
    spec: dict[str, object],
) -> Image.Image:
    output_tile_size = spec["output_tile_size"]
    visible_tile_size = spec["visible_tile_size"]
    source_offset = int(spec["source_offset"])
    tile = Image.new("RGBA", output_tile_size, (0, 0, 0, 0))
    source_start = column_index * visible_tile_size[0] + source_offset
    source_end = source_start + output_tile_size[0]
    crop_left = max(0, source_start)
    crop_right = min(canvas.width, source_end)
    if crop_right <= crop_left:
        return tile

    content = canvas.crop((crop_left, 0, crop_right, canvas.height))
    tile.alpha_composite(content, (crop_left - source_start, 0))
    return tile
