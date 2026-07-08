"""Slug and filename helpers."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def slugify(value: str, *, fallback: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or fallback


def safe_filename(filename: str, *, fallback_stem: str = "upload") -> str:
    path = Path(filename)
    stem = slugify(path.stem, fallback=fallback_stem)
    suffix = path.suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]+", suffix):
        suffix = ""
    return f"{stem}{suffix}"


def unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        next_candidate = directory / f"{stem}-{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1

