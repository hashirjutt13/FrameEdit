"""Configuration loading and normalization."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml


DEFAULT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


class ConfigError(ValueError):
    """Raised when a config file cannot be loaded or validated."""


@dataclass(frozen=True)
class LogoConfig:
    file: Path
    scale: float
    center: tuple[int, int]
    opacity: float


@dataclass(frozen=True)
class TextConfig:
    text: str
    font: Path | None
    size: int
    center: tuple[int, int]
    color: str
    auto_multiline: bool
    max_width: int | None
    line_spacing: float
    letter_spacing: float
    last_word_second_line: bool


@dataclass(frozen=True)
class PostConfig:
    size: tuple[int, int]
    default_vignette: str
    vignette_opacity: float
    vignettes: dict[str, Path]
    logo: LogoConfig


@dataclass(frozen=True)
class WebPVariantConfig:
    enabled: bool
    include_logo: bool
    lossless: bool
    quality: int
    method: int


@dataclass(frozen=True)
class BlackOverlayConfig:
    file: Path
    opacity: float


@dataclass(frozen=True)
class BackgroundBlurConfig:
    enabled: bool
    intensity: float
    max_radius: float

    @property
    def radius(self) -> float:
        return self.intensity * self.max_radius


@dataclass(frozen=True)
class ReelCoverConfig:
    size: tuple[int, int]
    background_blur: BackgroundBlurConfig
    black_overlay: BlackOverlayConfig
    logo: LogoConfig
    product_name: TextConfig
    category_name: TextConfig


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    input_dir: Path
    output_dir: Path
    supported_extensions: set[str]
    scan_recursive: bool
    aspect_ratio_tolerance: float
    overwrite: bool
    post: PostConfig
    webp_variant: WebPVariantConfig
    reel_cover: ReelCoverConfig

    def with_input_dir(self, input_dir: Path) -> "AppConfig":
        return replace(self, input_dir=input_dir)


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise ConfigError(f"Config file does not exist: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Could not parse YAML config {path}: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping.")

    return load_config_from_data(raw, base_dir=path.parent, config_path=path)


def load_config_from_data(
    raw: dict[str, Any],
    *,
    base_dir: Path,
    config_path: Path,
) -> AppConfig:
    """Build an app config from parsed YAML data.

    Web presets use the same schema as the CLI config, with a few extra
    metadata keys. Keeping this constructor public avoids writing temporary
    config files just to validate or render from a preset.
    """

    return AppConfig(
        config_path=config_path,
        input_dir=_path(raw, "input_dir", base_dir),
        output_dir=_path(raw, "output_dir", base_dir),
        supported_extensions=_extensions(raw.get("supported_extensions", DEFAULT_EXTENSIONS)),
        scan_recursive=bool(raw.get("scan_recursive", False)),
        aspect_ratio_tolerance=_float_range(
            raw.get("aspect_ratio_tolerance", 0.02),
            "aspect_ratio_tolerance",
            minimum=0.0,
            maximum=1.0,
            inclusive_min=False,
        ),
        overwrite=bool(raw.get("overwrite", True)),
        post=_post_config(_mapping(raw, "post"), base_dir),
        webp_variant=_webp_config(_mapping(raw, "webp_variant")),
        reel_cover=_reel_config(_mapping(raw, "reel_cover"), base_dir),
    )


def _post_config(data: dict[str, Any], base_dir: Path) -> PostConfig:
    vignettes_raw = _mapping(data, "vignettes")
    vignettes = {
        str(name): _resolve_path(value, base_dir, f"post.vignettes.{name}")
        for name, value in vignettes_raw.items()
    }
    default_vignette = str(data.get("default_vignette", "centered"))
    if default_vignette not in vignettes:
        raise ConfigError(
            f"post.default_vignette '{default_vignette}' is not defined in post.vignettes."
        )

    return PostConfig(
        size=_pair(data.get("size", [1080, 1440]), "post.size"),
        default_vignette=default_vignette,
        vignette_opacity=_float_range(
            data.get("vignette_opacity", 1.0),
            "post.vignette_opacity",
            minimum=0.0,
            maximum=1.0,
        ),
        vignettes=vignettes,
        logo=_logo_config(_mapping(data, "logo"), base_dir, "post.logo"),
    )


def _webp_config(data: dict[str, Any]) -> WebPVariantConfig:
    quality = _int(data.get("quality", 100), "webp_variant.quality")
    if not 0 <= quality <= 100:
        raise ConfigError("webp_variant.quality must be between 0 and 100.")

    method = _int(data.get("method", 6), "webp_variant.method")
    if not 0 <= method <= 6:
        raise ConfigError("webp_variant.method must be between 0 and 6.")

    return WebPVariantConfig(
        enabled=bool(data.get("enabled", True)),
        include_logo=bool(data.get("include_logo", True)),
        lossless=bool(data.get("lossless", True)),
        quality=quality,
        method=method,
    )


def _reel_config(data: dict[str, Any], base_dir: Path) -> ReelCoverConfig:
    overlay = _mapping(data, "black_overlay")
    return ReelCoverConfig(
        size=_pair(data.get("size", [1080, 1920]), "reel_cover.size"),
        background_blur=_background_blur_config(data.get("background_blur", {})),
        black_overlay=BlackOverlayConfig(
            file=_resolve_path(overlay.get("file"), base_dir, "reel_cover.black_overlay.file"),
            opacity=_float_range(
                overlay.get("opacity", 0.60),
                "reel_cover.black_overlay.opacity",
                minimum=0.0,
                maximum=1.0,
            ),
        ),
        logo=_logo_config(_mapping(data, "logo"), base_dir, "reel_cover.logo"),
        product_name=_text_config(
            _mapping(data, "product_name"),
            base_dir,
            "reel_cover.product_name",
            default_auto_multiline=True,
        ),
        category_name=_text_config(
            _mapping(data, "category_name"),
            base_dir,
            "reel_cover.category_name",
            default_auto_multiline=False,
        ),
    )


def _background_blur_config(value: Any) -> BackgroundBlurConfig:
    if value in (None, ""):
        value = {}
    if not isinstance(value, dict):
        raise ConfigError("reel_cover.background_blur must be a mapping.")

    return BackgroundBlurConfig(
        enabled=bool(value.get("enabled", False)),
        intensity=_float_range(
            value.get("intensity", 0.0),
            "reel_cover.background_blur.intensity",
            minimum=0.0,
            maximum=1.0,
        ),
        max_radius=_float_range(
            value.get("max_radius", 100.0),
            "reel_cover.background_blur.max_radius",
            minimum=0.0,
            maximum=500.0,
        ),
    )


def _logo_config(data: dict[str, Any], base_dir: Path, key: str) -> LogoConfig:
    return LogoConfig(
        file=_resolve_path(data.get("file"), base_dir, f"{key}.file"),
        scale=_float_range(
            data.get("scale", 0.2),
            f"{key}.scale",
            minimum=0.0,
            maximum=10.0,
            inclusive_min=False,
        ),
        center=_pair(data.get("center"), f"{key}.center"),
        opacity=_float_range(
            data.get("opacity", 1.0),
            f"{key}.opacity",
            minimum=0.0,
            maximum=1.0,
        ),
    )


def _text_config(
    data: dict[str, Any],
    base_dir: Path,
    key: str,
    *,
    default_auto_multiline: bool,
) -> TextConfig:
    font_value = data.get("font")
    font = None
    if font_value not in (None, ""):
        font = _resolve_path(font_value, base_dir, f"{key}.font")

    max_width_value = data.get("max_width")
    return TextConfig(
        text=str(data.get("text", "")),
        font=font,
        size=_int(data.get("size", 72), f"{key}.size"),
        center=_pair(data.get("center"), f"{key}.center"),
        color=str(data.get("color", "#ffffff")),
        auto_multiline=bool(data.get("auto_multiline", default_auto_multiline)),
        max_width=None if max_width_value in (None, "") else _int(max_width_value, f"{key}.max_width"),
        line_spacing=_float_range(
            data.get("line_spacing", 1.05),
            f"{key}.line_spacing",
            minimum=0.1,
            maximum=10.0,
            inclusive_min=False,
        ),
        letter_spacing=_float_range(
            data.get("letter_spacing", 0.0),
            f"{key}.letter_spacing",
            minimum=-1000.0,
            maximum=5000.0,
        ),
        last_word_second_line=bool(data.get("last_word_second_line", False)),
    )


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping.")
    return value


def _path(data: dict[str, Any], key: str, base_dir: Path) -> Path:
    if key not in data:
        raise ConfigError(f"Missing required config key: {key}")
    return _resolve_path(data[key], base_dir, key)


def _resolve_path(value: Any, base_dir: Path, key: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a non-empty path string.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _pair(value: Any, key: str) -> tuple[int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or not all(isinstance(item, int) for item in value)
    ):
        raise ConfigError(f"{key} must be a two-item integer list.")
    if value[0] <= 0 or value[1] <= 0:
        raise ConfigError(f"{key} values must be positive.")
    return int(value[0]), int(value[1])


def _int(value: Any, key: str) -> int:
    if not isinstance(value, int):
        raise ConfigError(f"{key} must be an integer.")
    return value


def _float_range(
    value: Any,
    key: str,
    *,
    minimum: float,
    maximum: float,
    inclusive_min: bool = True,
) -> float:
    if not isinstance(value, (int, float)):
        raise ConfigError(f"{key} must be a number.")
    result = float(value)
    min_ok = result >= minimum if inclusive_min else result > minimum
    if not min_ok or result > maximum:
        boundary = ">=" if inclusive_min else ">"
        raise ConfigError(f"{key} must be {boundary} {minimum} and <= {maximum}.")
    return result


def _extensions(values: Any) -> set[str]:
    if not isinstance(values, (set, list, tuple)):
        raise ConfigError("supported_extensions must be a list.")
    extensions = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ConfigError("Each supported extension must be a string.")
        ext = value.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        extensions.add(ext)
    if not extensions:
        raise ConfigError("supported_extensions cannot be empty.")
    return extensions
