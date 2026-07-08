"""Brand preset storage and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from frameedit.config import AppConfig, ConfigError, load_config_from_data

from .paths import PROJECT_ROOT, data_dir, ensure_data_dirs
from .slugs import slugify


DEFAULT_PRESET_SLUG = "starter-brand"


class PresetError(ValueError):
    """Raised when a brand preset cannot be loaded or saved."""


@dataclass(frozen=True)
class PresetSummary:
    name: str
    slug: str
    path: Path


@dataclass(frozen=True)
class BrandPreset:
    name: str
    slug: str
    path: Path
    raw: dict[str, Any]
    config: AppConfig


def presets_dir(root: Path | None = None) -> Path:
    base = ensure_data_dirs(root)
    return base / "presets"


def ensure_default_preset(root: Path | None = None) -> Path:
    directory = presets_dir(root)
    path = directory / f"{DEFAULT_PRESET_SLUG}.yaml"
    if not path.exists():
        source = PROJECT_ROOT / "config.yaml"
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise PresetError(f"Could not seed default preset from {source}")
        raw["brand"] = {"name": "Starter Brand", "slug": DEFAULT_PRESET_SLUG}
        _make_config_paths_absolute(raw, source.parent)
        path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def list_presets(root: Path | None = None) -> list[PresetSummary]:
    ensure_default_preset(root)
    summaries = []
    for path in sorted(presets_dir(root).glob("*.yaml")):
        raw = _read_yaml(path)
        brand = raw.get("brand", {}) if isinstance(raw.get("brand"), dict) else {}
        slug = str(brand.get("slug") or path.stem)
        name = str(brand.get("name") or slug.replace("-", " ").title())
        summaries.append(PresetSummary(name=name, slug=slug, path=path))
    return summaries


def load_preset(slug: str, root: Path | None = None) -> BrandPreset:
    ensure_default_preset(root)
    clean_slug = slugify(slug)
    path = presets_dir(root) / f"{clean_slug}.yaml"
    if not path.exists():
        raise PresetError(f"Preset does not exist: {clean_slug}")

    raw = _read_yaml(path)
    brand = raw.get("brand", {}) if isinstance(raw.get("brand"), dict) else {}
    name = str(brand.get("name") or clean_slug.replace("-", " ").title())
    actual_slug = slugify(str(brand.get("slug") or clean_slug))
    try:
        config = load_config_from_data(raw, base_dir=path.parent, config_path=path)
    except ConfigError as exc:
        raise PresetError(f"Invalid preset {clean_slug}: {exc}") from exc
    return BrandPreset(name=name, slug=actual_slug, path=path, raw=raw, config=config)


def save_preset(slug: str, raw: dict[str, Any], root: Path | None = None) -> BrandPreset:
    clean_slug = slugify(slug)
    raw = dict(raw)
    brand = raw.get("brand", {}) if isinstance(raw.get("brand"), dict) else {}
    brand["slug"] = clean_slug
    brand["name"] = str(brand.get("name") or clean_slug.replace("-", " ").title()).strip()
    raw["brand"] = brand

    directory = presets_dir(root)
    path = directory / f"{clean_slug}.yaml"
    try:
        load_config_from_data(raw, base_dir=path.parent, config_path=path)
    except ConfigError as exc:
        raise PresetError(str(exc)) from exc
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_preset(clean_slug, root)


def create_preset(name: str, root: Path | None = None) -> BrandPreset:
    default = load_preset(DEFAULT_PRESET_SLUG, root)
    slug = _available_slug(slugify(name, fallback="brand"), root)
    raw = dict(default.raw)
    raw["brand"] = {"name": name.strip() or slug.replace("-", " ").title(), "slug": slug}
    return save_preset(slug, raw, root)


def duplicate_preset(slug: str, root: Path | None = None) -> BrandPreset:
    preset = load_preset(slug, root)
    new_slug = _available_slug(f"{preset.slug}-copy", root)
    raw = dict(preset.raw)
    raw["brand"] = {"name": f"{preset.name} Copy", "slug": new_slug}
    return save_preset(new_slug, raw, root)


def rename_preset(slug: str, name: str, root: Path | None = None) -> BrandPreset:
    preset = load_preset(slug, root)
    new_slug = _available_slug(slugify(name, fallback=preset.slug), root, allow=preset.slug)
    raw = dict(preset.raw)
    raw["brand"] = {"name": name.strip() or preset.name, "slug": new_slug}
    if new_slug != preset.slug:
        preset.path.unlink()
    return save_preset(new_slug, raw, root)


def delete_preset(slug: str, root: Path | None = None) -> None:
    summaries = list_presets(root)
    if len(summaries) <= 1:
        raise PresetError("At least one preset is required.")
    preset = load_preset(slug, root)
    preset.path.unlink()


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PresetError(f"Could not parse preset {path}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise PresetError(f"Preset root must be a mapping: {path}")
    return raw


def _available_slug(slug: str, root: Path | None, *, allow: str | None = None) -> str:
    directory = presets_dir(root)
    if slug == allow or not (directory / f"{slug}.yaml").exists():
        return slug
    index = 2
    while True:
        candidate = f"{slug}-{index}"
        if candidate == allow or not (directory / f"{candidate}.yaml").exists():
            return candidate
        index += 1


def _make_config_paths_absolute(raw: dict[str, Any], base_dir: Path) -> None:
    if "input_dir" in raw:
        raw["input_dir"] = _absolute(raw["input_dir"], base_dir)
    if "output_dir" in raw:
        raw["output_dir"] = _absolute(raw["output_dir"], base_dir)

    post = raw.get("post", {})
    if isinstance(post, dict):
        logo = post.get("logo", {})
        if isinstance(logo, dict) and "file" in logo:
            logo["file"] = _absolute(logo["file"], base_dir)
        vignettes = post.get("vignettes", {})
        if isinstance(vignettes, dict):
            for key, value in list(vignettes.items()):
                vignettes[key] = _absolute(value, base_dir)

    reel = raw.get("reel_cover", {})
    if isinstance(reel, dict):
        overlay = reel.get("black_overlay", {})
        if isinstance(overlay, dict) and "file" in overlay:
            overlay["file"] = _absolute(overlay["file"], base_dir)
        logo = reel.get("logo", {})
        if isinstance(logo, dict) and "file" in logo:
            logo["file"] = _absolute(logo["file"], base_dir)
        for key in ("product_name", "category_name"):
            text = reel.get(key, {})
            if isinstance(text, dict) and text.get("font"):
                text["font"] = _absolute(text["font"], base_dir)


def _absolute(value: Any, base_dir: Path) -> Any:
    if not isinstance(value, str) or not value:
        return value
    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())
