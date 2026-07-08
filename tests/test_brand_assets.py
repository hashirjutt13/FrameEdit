from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "web_app" / "static" / "brand"


def _viewbox_ratio(path: Path) -> float:
    root = ElementTree.parse(path).getroot()
    viewbox = root.attrib["viewBox"]
    _, _, width, height = [float(part) for part in viewbox.split()]
    return width / height


def test_frameedit_logo_assets_are_horizontal() -> None:
    logo_concepts = sorted((BRAND_DIR / "concepts").glob("frameedit-logo-*.svg"))

    assert len(logo_concepts) == 6
    assert _viewbox_ratio(BRAND_DIR / "frameedit-logo.svg") >= 5
    for path in logo_concepts:
        assert _viewbox_ratio(path) >= 5


def test_frameedit_favicon_assets_exist_and_have_expected_sizes() -> None:
    favicon_concepts = sorted((BRAND_DIR / "concepts").glob("frameedit-favicon-*.svg"))

    assert len(favicon_concepts) == 3
    assert (BRAND_DIR / "frameedit-favicon.svg").exists()
    assert (BRAND_DIR / "favicon.ico").exists()

    expected_sizes = {
        "favicon-16.png": (16, 16),
        "favicon-32.png": (32, 32),
        "apple-touch-icon.png": (180, 180),
    }
    for filename, size in expected_sizes.items():
        with Image.open(BRAND_DIR / filename) as image:
            assert image.size == size
