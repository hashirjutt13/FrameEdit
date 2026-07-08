"""Saved carousel panorama storage."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .carousel_panorama import CarouselPanoramaResult
from .paths import ensure_data_dirs, path_within
from .slugs import slugify


@dataclass(frozen=True)
class CarouselProjectFile:
    path: Path
    relative_path: str
    name: str
    label: str
    slide_number: int
    upload_order: int


@dataclass(frozen=True)
class CarouselProjectRecord:
    name: str
    slug: str
    created_at: str
    path: Path
    zip_path: Path | None
    source_path: Path | None
    source_filename: str
    source_size: tuple[int, int]
    slide_format: str
    format_label: str
    aspect_ratio: str
    slide_count: int
    slide_size: tuple[int, int]
    working_canvas_size: tuple[int, int]
    fit_mode: str
    outputs: list[dict[str, Any]]


class CarouselProjectError(ValueError):
    """Raised when a saved carousel project cannot be managed."""


def carousel_projects_dir(root: Path | None = None) -> Path:
    return ensure_data_dirs(root) / "carousels"


def create_carousel_project_dir(
    carousel_name: str,
    *,
    root: Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    created_at = created_at or datetime.now()
    name_slug = slugify(carousel_name, fallback="carousel-panorama")
    date_prefix = created_at.strftime("%Y-%m-%d")
    base = carousel_projects_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    candidate = base / f"{date_prefix}-{name_slug}"
    if not candidate.exists():
        candidate.mkdir(parents=True)
        return candidate
    index = 2
    while True:
        next_candidate = base / f"{date_prefix}-{name_slug}-{index}"
        if not next_candidate.exists():
            next_candidate.mkdir(parents=True)
            return next_candidate
        index += 1


def write_carousel_metadata(
    project_path: Path,
    *,
    carousel_name: str,
    source_path: Path,
    zip_path: Path | None,
    result: CarouselPanoramaResult,
) -> CarouselProjectRecord:
    created_at = datetime.now().isoformat(timespec="seconds")
    metadata = {
        "name": carousel_name,
        "slug": project_path.name,
        "created_at": created_at,
        "zip_path": str(zip_path.relative_to(project_path)) if zip_path else "",
        "source_path": str(source_path.relative_to(project_path)),
        "source_filename": source_path.name,
        "source_size": list(result.source_size),
        "slide_format": result.slide_format,
        "format_label": result.format_label,
        "aspect_ratio": result.aspect_ratio,
        "slide_count": result.slide_count,
        "slide_size": list(result.slide_size),
        "working_canvas_size": list(result.working_canvas_size),
        "fit_mode": result.fit_mode,
        "outputs": [
            {
                "path": str(slide.path.relative_to(project_path)),
                "name": slide.path.name,
                "label": slide.label,
                "slide_number": slide.slide_number,
                "upload_order": slide.upload_order,
            }
            for slide in result.slides
        ],
    }
    (project_path / "carousel.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False),
        encoding="utf-8",
    )
    return load_carousel_project(project_path)


def load_carousel_project(path: Path) -> CarouselProjectRecord:
    metadata_path = path / "carousel.yaml"
    raw = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raw = {}
    zip_value = str(raw.get("zip_path") or "")
    source_value = str(raw.get("source_path") or "")
    return CarouselProjectRecord(
        name=str(raw.get("name") or path.name),
        slug=str(raw.get("slug") or path.name),
        created_at=str(raw.get("created_at") or ""),
        path=path,
        zip_path=path / zip_value if zip_value else None,
        source_path=path / source_value if source_value else None,
        source_filename=str(raw.get("source_filename") or Path(source_value).name),
        source_size=_pair(raw.get("source_size"), (0, 0)),
        slide_format=str(raw.get("slide_format") or ""),
        format_label=str(raw.get("format_label") or ""),
        aspect_ratio=str(raw.get("aspect_ratio") or ""),
        slide_count=_int(raw.get("slide_count"), 0),
        slide_size=_pair(raw.get("slide_size"), (0, 0)),
        working_canvas_size=_pair(raw.get("working_canvas_size"), (0, 0)),
        fit_mode=str(raw.get("fit_mode") or ""),
        outputs=list(raw.get("outputs") or []),
    )


def list_carousel_projects(
    *,
    root: Path | None = None,
    query: str = "",
) -> list[CarouselProjectRecord]:
    records: list[CarouselProjectRecord] = []
    for metadata_path in sorted(carousel_projects_dir(root).glob("*/carousel.yaml"), reverse=True):
        record = load_carousel_project(metadata_path.parent)
        if query and query.lower() not in record.name.lower():
            continue
        records.append(record)
    return records


def carousel_output_files(project: CarouselProjectRecord) -> list[CarouselProjectFile]:
    files: list[CarouselProjectFile] = []
    for item in project.outputs:
        if not isinstance(item, dict):
            continue
        path_value = item.get("path")
        if not path_value:
            continue
        relative_path = Path(str(path_value)).as_posix()
        files.append(
            CarouselProjectFile(
                path=project.path / relative_path,
                relative_path=relative_path,
                name=str(item.get("name") or Path(relative_path).name),
                label=str(item.get("label") or Path(relative_path).name),
                slide_number=_int(item.get("slide_number"), len(files) + 1),
                upload_order=_int(item.get("upload_order"), len(files) + 1),
            )
        )
    return files


def delete_carousel_project(slug: str, *, root: Path | None = None) -> None:
    base = carousel_projects_dir(root)
    target = base / slug
    if not path_within(target, base) or not (target / "carousel.yaml").exists():
        raise CarouselProjectError("Saved carousel does not exist.")
    shutil.rmtree(target)


def _pair(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (_int(value[0], default[0]), _int(value[1], default[1]))
    return default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
