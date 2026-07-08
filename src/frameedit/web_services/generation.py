"""Web-facing generation helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from frameedit.config import AppConfig
from frameedit.image_ops import register_heif_support
from frameedit.pipeline import AssetType, BatchError, classify_image
from frameedit.render import render_post_png, render_post_webp, render_reel_cover

from .slugs import slugify


VIGNETTE_UI_TO_CONFIG = {
    "center": "centered",
    "centered": "centered",
    "top": "top",
    "bottom": "bottom",
}


@dataclass(frozen=True)
class ClassifiedUpload:
    path: Path
    filename: str
    asset_type: AssetType
    size: tuple[int, int] | None
    ratio: float | None
    message: str = ""


@dataclass(frozen=True)
class UploadSet:
    posts: list[ClassifiedUpload]
    reels: list[ClassifiedUpload]
    unsupported: list[ClassifiedUpload]
    warnings: list[str]


@dataclass(frozen=True)
class GeneratedFile:
    kind: str
    path: Path
    label: str


def classify_uploads(paths: list[Path], config: AppConfig) -> UploadSet:
    heif_enabled = register_heif_support()
    posts: list[ClassifiedUpload] = []
    reels: list[ClassifiedUpload] = []
    unsupported: list[ClassifiedUpload] = []
    warnings: list[str] = []

    for path in paths:
        suffix = path.suffix.lower()
        if suffix not in config.supported_extensions:
            unsupported.append(
                ClassifiedUpload(
                    path=path,
                    filename=path.name,
                    asset_type=AssetType.UNSUPPORTED,
                    size=None,
                    ratio=None,
                    message=f"Unsupported file type: {suffix or 'unknown'}",
                )
            )
            continue
        if suffix in {".heic", ".heif"} and not heif_enabled:
            raise BatchError("HEIC/HEIF input found, but pillow-heif is not installed.")

        item = classify_image(path, config.aspect_ratio_tolerance)
        record = ClassifiedUpload(
            path=path,
            filename=path.name,
            asset_type=item.asset_type,
            size=item.size,
            ratio=item.ratio,
        )
        if item.asset_type == AssetType.POST:
            posts.append(record)
        elif item.asset_type == AssetType.REEL:
            reels.append(record)
        else:
            unsupported.append(
                replace(
                    record,
                    message=(
                        f"Unsupported aspect ratio: {item.size[0]}x{item.size[1]} "
                        f"({item.ratio:.4f})"
                    ),
                )
            )

    if not reels:
        warnings.append("No reel-cover image found.")
    if len(reels) > 1:
        warnings.append("More than one 9:16 image found; choose one for the reel cover.")

    return UploadSet(posts=posts, reels=reels, unsupported=unsupported, warnings=warnings)


def config_for_run(
    config: AppConfig,
    *,
    output_dir: Path,
    product_name: str | None = None,
    category_name: str | None = None,
) -> AppConfig:
    reel = config.reel_cover
    product = reel.product_name
    category = reel.category_name
    if product_name is not None:
        product = replace(product, text=normalize_product_name(product_name))
    if category_name is not None:
        category = replace(category, text=normalize_category_name(category_name))
    reel = replace(reel, product_name=product, category_name=category)
    return replace(config, output_dir=output_dir, reel_cover=reel)


def render_post_outputs(
    config: AppConfig,
    posts: list[Path],
    *,
    output_dir: Path,
    product_name: str,
    vignette_choices: dict[int, str] | None = None,
    include_webp: bool = True,
    output_stems: list[str] | None = None,
) -> list[GeneratedFile]:
    run_config = config_for_run(config, output_dir=output_dir)
    product_slug = slugify(product_name, fallback="product")
    results: list[GeneratedFile] = []
    vignette_choices = vignette_choices or {}
    output_stems = output_stems or []

    for index, source in enumerate(posts, start=1):
        stem = output_stems[index - 1] if index - 1 < len(output_stems) else f"{product_slug}-post-{index:02d}"
        vignette_name = normalize_vignette(vignette_choices.get(index - 1), config)
        post_target = output_dir / "posts_instagram" / f"{stem}.png"
        render_post_png(source, post_target, run_config, vignette_name=vignette_name)
        results.append(GeneratedFile(kind="post_png", path=post_target, label=f"Post {index:02d} PNG"))

        if include_webp and config.webp_variant.enabled:
            webp_target = output_dir / "posts_webp_no_vignette" / f"{stem}.webp"
            render_post_webp(source, webp_target, run_config)
            results.append(GeneratedFile(kind="post_webp", path=webp_target, label=f"Post {index:02d} WebP"))

    return results


def render_reel_output(
    config: AppConfig,
    source: Path,
    *,
    output_dir: Path,
    product_name: str,
    category_name: str,
) -> GeneratedFile:
    product_name = normalize_product_name(product_name)
    category_name = normalize_category_name(category_name)
    run_config = config_for_run(
        config,
        output_dir=output_dir,
        product_name=product_name,
        category_name=category_name,
    )
    product_slug = slugify(product_name, fallback="product")
    target = output_dir / "reel_cover" / f"{product_slug}-reel-cover.png"
    render_reel_cover(source, target, run_config)
    return GeneratedFile(kind="reel_cover", path=target, label="Reel Cover")


def normalize_vignette(choice: str | None, config: AppConfig) -> str:
    if not choice:
        return config.post.default_vignette
    mapped = VIGNETTE_UI_TO_CONFIG.get(choice, choice)
    if mapped not in config.post.vignettes:
        return config.post.default_vignette
    return mapped


def normalize_product_name(value: str) -> str:
    return " ".join(value.split()).upper()


def normalize_category_name(value: str) -> str:
    words = []
    for word in value.split():
        if not word:
            continue
        words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)
