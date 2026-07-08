"""Batch planning, validation, and execution."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image, ImageOps

from .config import AppConfig
from .image_ops import register_heif_support
from .render import render_post_png, render_post_webp, render_reel_cover


POST_RATIO = 3 / 4
REEL_RATIO = 9 / 16


class AssetType(str, Enum):
    POST = "post"
    REEL = "reel"
    UNSUPPORTED = "unsupported"


class BatchError(RuntimeError):
    """Raised when a batch cannot be planned or rendered."""


@dataclass(frozen=True)
class ImageClassification:
    path: Path
    asset_type: AssetType
    size: tuple[int, int]
    ratio: float


@dataclass(frozen=True)
class PlannedOutput:
    kind: str
    source: Path
    target: Path


@dataclass(frozen=True)
class BatchPlan:
    outputs: list[PlannedOutput]
    warnings: list[str]


@dataclass(frozen=True)
class BatchResult:
    outputs: list[PlannedOutput]
    warnings: list[str]
    dry_run: bool


def run_batch(config: AppConfig, *, dry_run: bool = False) -> BatchResult:
    heif_enabled = register_heif_support()
    plan = plan_batch(config, heif_enabled=heif_enabled)

    if dry_run:
        return BatchResult(outputs=plan.outputs, warnings=plan.warnings, dry_run=True)

    if not config.overwrite:
        existing = [output.target for output in plan.outputs if output.target.exists()]
        if existing:
            formatted = "\n".join(f"- {path}" for path in existing)
            raise BatchError(f"Refusing to overwrite existing outputs:\n{formatted}")

    for output in plan.outputs:
        if output.kind == "post_png":
            render_post_png(output.source, output.target, config)
        elif output.kind == "post_webp":
            render_post_webp(output.source, output.target, config)
        elif output.kind == "reel_cover":
            render_reel_cover(output.source, output.target, config)
        else:
            raise BatchError(f"Unknown output kind: {output.kind}")

    return BatchResult(outputs=plan.outputs, warnings=plan.warnings, dry_run=False)


def plan_batch(config: AppConfig, *, heif_enabled: bool = True) -> BatchPlan:
    warnings: list[str] = []
    images = discover_images(config)

    if not images:
        warnings.append("No supported input images found.")
    if not heif_enabled and any(path.suffix.lower() in {".heic", ".heif"} for path in images):
        raise BatchError("HEIC/HEIF input found, but pillow-heif is not installed.")

    classifications = [classify_image(path, config.aspect_ratio_tolerance) for path in images]

    unsupported = [item for item in classifications if item.asset_type == AssetType.UNSUPPORTED]
    for item in unsupported:
        warnings.append(
            f"Unsupported aspect ratio for {item.path.name}: "
            f"{item.size[0]}x{item.size[1]} ({item.ratio:.4f})."
        )

    posts = [item for item in classifications if item.asset_type == AssetType.POST]
    reels = [item for item in classifications if item.asset_type == AssetType.REEL]

    if not reels:
        warnings.append("No reel-cover image found.")
    if len(reels) > 1:
        warnings.append(
            "More than one 9:16 image found; using the first reel-cover candidate: "
            f"{reels[0].path.name}."
        )

    _validate_assets(config, has_posts=bool(posts), has_reel=bool(reels))

    outputs: list[PlannedOutput] = []
    for post in posts:
        outputs.append(
            PlannedOutput(
                kind="post_png",
                source=post.path,
                target=config.output_dir / "posts_instagram" / f"{post.path.stem}.png",
            )
        )
        if config.webp_variant.enabled:
            outputs.append(
                PlannedOutput(
                    kind="post_webp",
                    source=post.path,
                    target=config.output_dir / "posts_webp_no_vignette" / f"{post.path.stem}.webp",
                )
            )

    if reels:
        outputs.append(
            PlannedOutput(
                kind="reel_cover",
                source=reels[0].path,
                target=config.output_dir / "reel_cover" / "reel-cover.png",
            )
        )

    _validate_output_collisions(outputs)
    return BatchPlan(outputs=outputs, warnings=warnings)


def discover_images(config: AppConfig) -> list[Path]:
    if not config.input_dir.exists():
        raise BatchError(f"Input directory does not exist: {config.input_dir}")
    if not config.input_dir.is_dir():
        raise BatchError(f"Input path is not a directory: {config.input_dir}")

    iterator = config.input_dir.rglob("*") if config.scan_recursive else config.input_dir.iterdir()
    return sorted(
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in config.supported_extensions
    )


def classify_image(path: Path, tolerance: float) -> ImageClassification:
    try:
        with Image.open(path) as image:
            oriented = ImageOps.exif_transpose(image)
            size = oriented.size
    except OSError as exc:
        raise BatchError(f"Could not open image {path}: {exc}") from exc

    ratio = size[0] / size[1]
    if math.isclose(ratio, POST_RATIO, rel_tol=tolerance):
        asset_type = AssetType.POST
    elif math.isclose(ratio, REEL_RATIO, rel_tol=tolerance):
        asset_type = AssetType.REEL
    else:
        asset_type = AssetType.UNSUPPORTED

    return ImageClassification(path=path, asset_type=asset_type, size=size, ratio=ratio)


def _validate_assets(config: AppConfig, *, has_posts: bool, has_reel: bool) -> None:
    errors: list[str] = []

    if has_posts:
        _require_file(config.post.logo.file, "post.logo.file", errors)
        for name, path in config.post.vignettes.items():
            _require_file(path, f"post.vignettes.{name}", errors)
            _require_overlay_size(path, config.post.size, f"post.vignettes.{name}", errors)

    if has_reel:
        _require_file(config.reel_cover.black_overlay.file, "reel_cover.black_overlay.file", errors)
        _require_file(config.reel_cover.logo.file, "reel_cover.logo.file", errors)
        _require_overlay_size(
            config.reel_cover.black_overlay.file,
            config.reel_cover.size,
            "reel_cover.black_overlay.file",
            errors,
        )
        if config.reel_cover.product_name.font is not None:
            _require_file(
                config.reel_cover.product_name.font,
                "reel_cover.product_name.font",
                errors,
            )
        if config.reel_cover.category_name.font is not None:
            _require_file(
                config.reel_cover.category_name.font,
                "reel_cover.category_name.font",
                errors,
            )

    if errors:
        raise BatchError("Validation failed:\n" + "\n".join(f"- {error}" for error in errors))


def _require_file(path: Path, label: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"{label} does not exist: {path}")
    elif not path.is_file():
        errors.append(f"{label} is not a file: {path}")


def _require_overlay_size(
    path: Path,
    expected_size: tuple[int, int],
    label: str,
    errors: list[str],
) -> None:
    if not path.exists() or not path.is_file():
        return
    try:
        with Image.open(path) as image:
            actual_size = image.size
    except OSError as exc:
        errors.append(f"{label} could not be opened: {exc}")
        return

    if actual_size != expected_size:
        errors.append(
            f"{label} is {actual_size[0]}x{actual_size[1]}, "
            f"expected {expected_size[0]}x{expected_size[1]}."
        )


def _validate_output_collisions(outputs: list[PlannedOutput]) -> None:
    seen: dict[Path, PlannedOutput] = {}
    collisions: list[str] = []
    for output in outputs:
        if output.target in seen:
            previous = seen[output.target]
            collisions.append(
                f"{output.target} would be written by both {previous.source.name} and {output.source.name}."
            )
        seen[output.target] = output

    if collisions:
        raise BatchError("Output filename collision:\n" + "\n".join(f"- {item}" for item in collisions))
