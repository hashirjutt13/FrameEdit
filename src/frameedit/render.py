"""Render post and reel-cover outputs."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

from .config import AppConfig
from .image_ops import (
    composite_center,
    draw_centered_text_block,
    fit_to_size,
    open_layer,
    open_oriented_image,
    scale_logo,
    with_opacity,
)


def render_post_png(
    source: Path,
    target: Path,
    config: AppConfig,
    *,
    vignette_name: str | None = None,
) -> None:
    post = config.post
    base = fit_to_size(open_oriented_image(source), post.size)
    selected_vignette = vignette_name or post.default_vignette
    vignette_path = post.vignettes[selected_vignette]
    vignette = with_opacity(open_layer(vignette_path, post.size), post.vignette_opacity)
    base.alpha_composite(vignette)

    logo = scale_logo(open_layer(post.logo.file), post.logo, post.size)
    result = composite_center(base, logo, post.logo.center)
    _save_png(result, target)


def render_post_webp(source: Path, target: Path, config: AppConfig) -> None:
    post = config.post
    webp = config.webp_variant
    result = fit_to_size(open_oriented_image(source), post.size)

    if webp.include_logo:
        logo = scale_logo(open_layer(post.logo.file), post.logo, post.size)
        result = composite_center(result, logo, post.logo.center)

    target.parent.mkdir(parents=True, exist_ok=True)
    result.save(
        target,
        format="WEBP",
        lossless=webp.lossless,
        quality=webp.quality,
        method=webp.method,
    )


def render_reel_cover(source: Path, target: Path, config: AppConfig) -> None:
    reel = config.reel_cover
    result = fit_to_size(open_oriented_image(source), reel.size)
    if reel.background_blur.enabled and reel.background_blur.radius > 0:
        result = result.filter(ImageFilter.GaussianBlur(radius=reel.background_blur.radius))

    black_overlay = with_opacity(
        open_layer(reel.black_overlay.file, reel.size),
        reel.black_overlay.opacity,
    )
    result.alpha_composite(black_overlay)

    logo = scale_logo(open_layer(reel.logo.file), reel.logo, reel.size)
    result = composite_center(result, logo, reel.logo.center)
    result = draw_centered_text_block(result, reel.product_name)
    result = draw_centered_text_block(result, reel.category_name)
    _save_png(result, target)


def _save_png(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG")
