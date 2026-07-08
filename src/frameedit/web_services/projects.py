"""Saved project storage for All In One jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .paths import ensure_data_dirs
from .slugs import slugify


@dataclass(frozen=True)
class ProjectRecord:
    brand_name: str
    brand_slug: str
    product_name: str
    product_slug: str
    created_at: str
    path: Path
    zip_path: Path | None
    outputs: list[dict[str, str]]
    grid_layout: list[str]


@dataclass(frozen=True)
class GridCandidate:
    path: Path
    relative_path: str
    name: str
    kind: str


class ProjectGridError(ValueError):
    """Raised when a saved grid layout is invalid for the project."""


def projects_dir(root: Path | None = None) -> Path:
    return ensure_data_dirs(root) / "projects"


def create_project_dir(
    *,
    brand_name: str,
    brand_slug: str,
    product_name: str,
    root: Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    created_at = created_at or datetime.now()
    product_slug = slugify(product_name, fallback="product")
    date_prefix = created_at.strftime("%Y-%m-%d")
    base = projects_dir(root) / brand_slug
    base.mkdir(parents=True, exist_ok=True)
    candidate = base / f"{date_prefix}-{product_slug}"
    if not candidate.exists():
        candidate.mkdir(parents=True)
        return candidate
    index = 2
    while True:
        next_candidate = base / f"{date_prefix}-{product_slug}-{index}"
        if not next_candidate.exists():
            next_candidate.mkdir(parents=True)
            return next_candidate
        index += 1


def write_project_metadata(
    project_path: Path,
    *,
    brand_name: str,
    brand_slug: str,
    product_name: str,
    zip_path: Path | None,
    outputs: list[Path],
) -> ProjectRecord:
    created_at = datetime.now().isoformat(timespec="seconds")
    product_slug = slugify(product_name, fallback="product")
    metadata = {
        "brand_name": brand_name,
        "brand_slug": brand_slug,
        "product_name": product_name,
        "product_slug": product_slug,
        "created_at": created_at,
        "zip_path": str(zip_path.relative_to(project_path)) if zip_path else "",
        "outputs": [
            {"path": str(path.relative_to(project_path)), "name": path.name}
            for path in outputs
        ],
    }
    (project_path / "project.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False),
        encoding="utf-8",
    )
    return load_project(project_path)


def load_project(path: Path) -> ProjectRecord:
    metadata_path = path / "project.yaml"
    raw = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raw = {}
    zip_value = str(raw.get("zip_path") or "")
    zip_path = path / zip_value if zip_value else None
    return ProjectRecord(
        brand_name=str(raw.get("brand_name") or ""),
        brand_slug=str(raw.get("brand_slug") or path.parent.name),
        product_name=str(raw.get("product_name") or ""),
        product_slug=str(raw.get("product_slug") or path.name),
        created_at=str(raw.get("created_at") or ""),
        path=path,
        zip_path=zip_path,
        outputs=list(raw.get("outputs") or []),
        grid_layout=[str(item) for item in raw.get("grid_layout") or []],
    )


def list_projects(
    *,
    root: Path | None = None,
    query: str = "",
    brand_slug: str = "",
) -> list[ProjectRecord]:
    base = projects_dir(root)
    records: list[ProjectRecord] = []
    for metadata_path in sorted(base.glob("*/*/project.yaml"), reverse=True):
        record = load_project(metadata_path.parent)
        if brand_slug and record.brand_slug != brand_slug:
            continue
        haystack = f"{record.brand_name} {record.product_name}".lower()
        if query and query.lower() not in haystack:
            continue
        records.append(record)
    return records


def project_output_files(project: ProjectRecord) -> list[Path]:
    files = []
    for item in project.outputs:
        if not isinstance(item, dict):
            continue
        path_value = item.get("path")
        if not path_value:
            continue
        files.append(project.path / str(path_value))
    return files


def project_grid_candidates(project: ProjectRecord) -> list[GridCandidate]:
    candidates: list[GridCandidate] = []
    for item in project.outputs:
        if not isinstance(item, dict):
            continue
        path_value = item.get("path")
        if not path_value:
            continue
        relative_path = Path(str(path_value)).as_posix()
        kind = _grid_candidate_kind(relative_path)
        if not kind:
            continue
        candidates.append(
            GridCandidate(
                path=project.path / relative_path,
                relative_path=relative_path,
                name=str(item.get("name") or Path(relative_path).name),
                kind=kind,
            )
        )
    return candidates


def default_grid_layout(project: ProjectRecord) -> list[str]:
    candidates = project_grid_candidates(project)
    posts = [candidate.relative_path for candidate in candidates if candidate.kind == "post"]
    reels = [candidate.relative_path for candidate in candidates if candidate.kind == "reel"]
    if not posts or not reels:
        return []
    right_post = posts[1] if len(posts) > 1 else posts[0]
    return [posts[0], reels[0], right_post]


def project_grid_layout(project: ProjectRecord) -> list[str]:
    valid_paths = {candidate.relative_path for candidate in project_grid_candidates(project)}
    if len(project.grid_layout) == 3 and all(path in valid_paths for path in project.grid_layout):
        return project.grid_layout
    return default_grid_layout(project)


def save_project_grid_layout(project_path: Path, layout: list[str]) -> ProjectRecord:
    project = load_project(project_path)
    valid_paths = {candidate.relative_path for candidate in project_grid_candidates(project)}
    normalized = [Path(str(item)).as_posix() for item in layout]
    if len(normalized) != 3:
        raise ProjectGridError("Choose exactly three grid items.")
    invalid = [path for path in normalized if path not in valid_paths]
    if invalid:
        raise ProjectGridError("Grid layout contains an unknown project file.")

    metadata_path = project_path / "project.yaml"
    raw = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raw = {}
    raw["grid_layout"] = normalized
    metadata_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    return load_project(project_path)


def _grid_candidate_kind(relative_path: str) -> str:
    path = Path(relative_path)
    if path.suffix.lower() != ".png":
        return ""
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "posts_instagram":
        return "post"
    if len(parts) >= 2 and parts[0] == "reel_cover":
        return "reel"
    return ""
