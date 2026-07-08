<p align="center">
  <img src="web_app/static/brand/frameedit-logo.svg" alt="FrameEdit" width="360">
</p>

<p align="center">
  Local-first image production for branded Instagram posts, reel covers, profile mosaics, and panorama carousels.
</p>

<p align="center">
  <strong>Python</strong> · <strong>Flask</strong> · <strong>Pillow</strong> · <strong>YAML presets</strong> · <strong>cPanel friendly</strong>
</p>

# FrameEdit

FrameEdit turns a folder of product images into ready-to-post social assets with repeatable brand rules. It keeps the generation engine local, deterministic, and configurable so teams can move faster without rebuilding the same layout by hand every time.

## Pain Points It Solves

- Manual Canva repetition: resize, crop, logo placement, overlays, text, and exports are handled in one run.
- Brand drift: logo positions, font choices, colors, blur, opacity, and vignette choices live in YAML presets.
- Wrong formats: images are classified by aspect ratio and invalid uploads are rejected early.
- Messy handoff: PNG, WebP, reel-cover, grid, carousel, and ZIP outputs are grouped into predictable folders.
- Hosting friction: the Web UI uses Flask and plain CSS, with no required Node build step or internet dependency at runtime.

## Features

- Batch-generate `1080 x 1440` Instagram post PNGs.
- Generate no-vignette lossless WebP variants for post images.
- Generate `1080 x 1920` reel covers with overlay, logo, product text, category text, and optional background blur.
- Classify `3:4` images as posts and `9:16` images as reel-cover candidates.
- Support `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, and `.heif`.
- Manage editable brand presets and reusable assets from the Web UI.
- Save All In One projects with ZIP downloads and previous-work browsing.
- Split wide images into profile grid mosaics and Instagram carousel panoramas.
- Optional password gate for lightweight private deployments.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

The repository ships with placeholder assets, so it can run immediately after install.

## CLI Usage

Place supported input images in `input/`, then run a dry run:

```bash
.venv/bin/python generate.py --config config.yaml --dry-run
```

Generate files:

```bash
.venv/bin/python generate.py --config config.yaml
```

Override the configured input folder:

```bash
.venv/bin/python generate.py /path/to/images --config config.yaml
```

If installed as a package, you can also use the console command:

```bash
frameedit --config config.yaml --dry-run
```

## Web UI Usage

Run the Flask app locally:

```bash
.venv/bin/python -m flask --app web_app.app run --debug
```

Open:

```text
http://127.0.0.1:5000
```

The Web UI includes:

- All In One: upload a full product batch, preview, choose vignettes, generate, save, and ZIP.
- Posts: generate post PNG/WebP assets only.
- Reel Cover: generate one reel cover only.
- Grid Mosaic: split one horizontal image into a 3-column profile mosaic.
- Carousel: split one panorama into 2-20 Instagram carousel slides.
- Settings: manage presets and upload reusable logos, fonts, and vignettes.

## Demo Documentation

- [Mahogany Furniture demo walkthrough](docs/mahogany-demo-walkthrough.md)
- [LinkedIn launch post guide](docs/linkedin-post-guide.md)

## Output Structure

```text
output/
  posts_instagram/
  posts_webp_no_vignette/
  reel_cover/
```

Web UI projects and ZIPs use the same grouped output folders, plus optional `grid_mosaic/` and `carousel_panorama/` folders when those tools are used.

## Configuration

Edit `config.yaml` for CLI defaults. The Web UI stores editable presets as YAML under:

```text
data/presets/
```

The included preset is:

```text
data/presets/starter-brand.yaml
```

Runtime data defaults to `data/`. To store uploads, presets, generated projects, and ZIPs elsewhere:

```bash
export FRAMEEDIT_DATA_DIR=/path/to/frameedit-data
```

Optional Web UI environment variables:

```text
WEB_UI_PASSWORD=your-password
WEB_UI_SECRET_KEY=long-random-secret
WEB_UI_MAX_UPLOAD_MB=512
FRAMEEDIT_DATA_DIR=/path/to/frameedit-data
```

## Assets

Starter assets live in `assets/`:

- `assets/logo-placeholder.png`
- `assets/vignettes/centered.png`
- `assets/vignettes/top.png`
- `assets/vignettes/bottom.png`
- `assets/black_9x16.png`

Licensed fonts and brand-specific files should stay local and untracked. See `assets/fonts/README.md`.

## Deployment

FrameEdit is designed for cPanel Python App / Passenger hosting. See `docs/cpanel-deployment.md` for setup notes.

The app can run without internet access at runtime after dependencies and assets are installed.
