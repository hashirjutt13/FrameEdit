"""ZIP packaging helpers."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


OUTPUT_FOLDERS = (
    "posts_instagram",
    "posts_webp_no_vignette",
    "reel_cover",
    "grid_mosaic",
    "carousel_panorama",
)


def create_output_zip(output_root: Path, *, zip_path: Path, archive_root: str) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for folder in OUTPUT_FOLDERS:
            directory = output_root / folder
            if not directory.exists():
                continue
            for path in sorted(directory.iterdir()):
                if path.is_file():
                    archive.write(path, Path(archive_root) / folder / path.name)
    return zip_path
