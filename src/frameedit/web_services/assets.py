"""Reusable asset library for uploaded logos, fonts, and vignettes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from .paths import PROJECT_ROOT, ensure_data_dirs
from .slugs import safe_filename, unique_path


ASSET_EXTENSIONS = {
    "logos": {".png", ".jpg", ".jpeg", ".webp"},
    "fonts": {".ttf", ".otf"},
    "vignettes": {".png"},
}


class AssetError(ValueError):
    """Raised when an uploaded asset is invalid."""


@dataclass(frozen=True)
class AssetRecord:
    kind: str
    name: str
    path: Path


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
    records.extend(_builtin_assets(kind, allowed))
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
