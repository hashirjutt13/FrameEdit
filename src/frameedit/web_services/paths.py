"""Filesystem paths used by the Web UI services."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    return Path(os.environ.get("FRAMEEDIT_DATA_DIR", PROJECT_ROOT / "data")).expanduser().resolve()


def ensure_data_dirs(root: Path | None = None) -> Path:
    base = (root or data_dir()).resolve()
    for child in [
        base / "presets",
        base / "assets" / "logos",
        base / "assets" / "fonts",
        base / "assets" / "vignettes",
        base / "carousels",
        base / "projects",
        base / "temp",
    ]:
        child.mkdir(parents=True, exist_ok=True)
    return base


def path_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True
