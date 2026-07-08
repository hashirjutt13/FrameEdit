"""Reusable asset library for uploaded logos, fonts, and vignettes."""

from __future__ import annotations

import filecmp
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from .paths import PROJECT_ROOT, ensure_data_dirs
from .slugs import safe_filename, unique_path


ASSET_EXTENSIONS = {
    "logos": {".png", ".jpg", ".jpeg", ".webp", ".svg"},
    "fonts": {".ttf", ".otf"},
    "vignettes": {".png"},
}

LOCAL_ASSET_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "env",
    "input",
    "output",
    "venv",
}


class AssetError(ValueError):
    """Raised when an uploaded asset is invalid."""


@dataclass(frozen=True)
class AssetRecord:
    kind: str
    name: str
    path: Path


@dataclass(frozen=True)
class AssetSeedResult:
    imported: list[AssetRecord]
    skipped: list[AssetRecord]


def asset_dir(kind: str, root: Path | None = None) -> Path:
    if kind not in ASSET_EXTENSIONS:
        raise AssetError(f"Unknown asset kind: {kind}")
    return ensure_data_dirs(root) / "assets" / kind


def list_assets(kind: str, root: Path | None = None) -> list[AssetRecord]:
    directory = asset_dir(kind, root)
    allowed = ASSET_EXTENSIONS[kind]
    records = [
        AssetRecord(kind=kind, name=path.name, path=path)
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() in allowed
    ]
    seen = {record.name for record in records}
    for record in _builtin_assets(kind, allowed):
        if record.name not in seen:
            records.append(record)
            seen.add(record.name)
    return records


def save_asset_upload(upload: object, kind: str, root: Path | None = None) -> AssetRecord:
    filename = str(getattr(upload, "filename", "") or "")
    if not filename.strip():
        raise AssetError("Choose a file to upload.")

    safe_name = safe_filename(filename, fallback_stem=kind[:-1] or "asset")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ASSET_EXTENSIONS[kind]:
        allowed = ", ".join(sorted(ASSET_EXTENSIONS[kind]))
        raise AssetError(f"{kind.title()} must use one of: {allowed}")

    directory = asset_dir(kind, root)
    target = unique_path(directory, safe_name)
    save = getattr(upload, "save", None)
    if callable(save):
        save(target)
    else:
        stream = getattr(upload, "stream", upload)
        _copy_stream(stream, target)
    return AssetRecord(kind=kind, name=target.name, path=target)


def seed_local_assets(
    root: Path | None = None,
    *,
    source_root: Path | None = None,
) -> AssetSeedResult:
    """Copy logo/font files already in the project into the Web UI asset library."""

    base = ensure_data_dirs(root)
    source = (source_root or PROJECT_ROOT).resolve()
    imported: list[AssetRecord] = []
    skipped: list[AssetRecord] = []

    for kind, path in _local_asset_candidates(source):
        target_dir = asset_dir(kind, base)
        safe_name = safe_filename(path.name, fallback_stem=kind[:-1] or "asset")
        existing = target_dir / safe_name
        if existing.exists() and filecmp.cmp(path, existing, shallow=False):
            skipped.append(AssetRecord(kind=kind, name=existing.name, path=existing))
            continue

        target = existing if not existing.exists() else unique_path(target_dir, safe_name)
        shutil.copy2(path, target)
        imported.append(AssetRecord(kind=kind, name=target.name, path=target))

    return AssetSeedResult(imported=imported, skipped=skipped)


def _copy_stream(stream: BinaryIO, target: Path) -> None:
    with target.open("wb") as handle:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)


def _builtin_assets(kind: str, allowed: set[str]) -> list[AssetRecord]:
    if kind == "logos":
        candidates = [PROJECT_ROOT / "assets" / "logo-placeholder.png"]
    elif kind == "fonts":
        candidates = sorted((PROJECT_ROOT / "assets" / "fonts").glob("*"))
    elif kind == "vignettes":
        candidates = sorted((PROJECT_ROOT / "assets" / "vignettes").glob("*"))
    else:
        candidates = []
    return [
        AssetRecord(kind=kind, name=path.name, path=path)
        for path in candidates
        if path.is_file() and path.suffix.lower() in allowed
    ]


def _local_asset_candidates(source_root: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or _is_excluded_local_asset_path(path, source_root):
            continue

        suffix = path.suffix.lower()
        if suffix in ASSET_EXTENSIONS["fonts"]:
            candidates.append(("fonts", path))
        elif suffix in ASSET_EXTENSIONS["logos"] and _is_logo_candidate(path, source_root):
            candidates.append(("logos", path))
    return candidates


def _is_logo_candidate(path: Path, source_root: Path) -> bool:
    if "logo" in path.stem.lower():
        return True
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        return False
    return any(part.lower() == "logos" for part in relative.parts[:-1])


def _is_excluded_local_asset_path(path: Path, source_root: Path) -> bool:
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        return True
    return any(part in LOCAL_ASSET_EXCLUDED_DIRS for part in relative.parts)
