"""cPanel Passenger WSGI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path


def configure_data_dir(project_root: Path) -> None:
    external_data_dir = project_root.with_name(f"{project_root.name}-data")
    if "FRAMEEDIT_DATA_DIR" not in os.environ and external_data_dir.exists():
        os.environ["FRAMEEDIT_DATA_DIR"] = str(external_data_dir)


configure_data_dir(Path(__file__).resolve().parent)

from web_app.app import app as application
