# cPanel Deployment

FrameEdit is designed to run on cPanel's Python Application / Passenger support.

## Files

- Flask app factory: `web_app.app:create_app`
- Passenger entrypoint: `passenger_wsgi.py`
- Default runtime data: `data/`

## Basic Setup

1. Upload or clone the project to your cPanel account.
2. Create a Python app in cPanel and point it at the project directory.
3. Set the startup file to `passenger_wsgi.py` if cPanel asks.
4. Install dependencies in the app virtualenv:

```bash
pip install -e .
```

5. Make sure the runtime data directory is writable by the app.

## Environment

Optional variables:

```text
WEB_UI_PASSWORD=your-password
WEB_UI_SECRET_KEY=long-random-secret
WEB_UI_MAX_UPLOAD_MB=512
FRAMEEDIT_DATA_DIR=/home/ismails1/framekit-data
```

If `WEB_UI_PASSWORD` is empty or missing, the UI is not password protected.

Use `FRAMEEDIT_DATA_DIR` when you want uploads, presets, generated projects, and ZIP files outside the deployed code directory.
On Passenger/cPanel, `passenger_wsgi.py` automatically uses a sibling `framekit-data` directory when `FRAMEEDIT_DATA_DIR` is not set and that directory exists.

## Runtime Folders

Create these folders under `FRAMEEDIT_DATA_DIR`:

```text
presets/
assets/logos/
assets/fonts/
assets/vignettes/
assets/overlays/
projects/
carousels/
temp/
```

## Asset Setup

Upload brand assets to runtime storage, for example:

```text
/home/ismails1/framekit-data/assets/logos/brand-logo.png
/home/ismails1/framekit-data/assets/fonts/product-font.otf
/home/ismails1/framekit-data/assets/fonts/category-font.ttf
/home/ismails1/framekit-data/assets/vignettes/centered.png
/home/ismails1/framekit-data/assets/vignettes/top.png
/home/ismails1/framekit-data/assets/vignettes/bottom.png
/home/ismails1/framekit-data/assets/overlays/black_9x16.png
```

Then update the preset YAML to point at those files. Relative paths are resolved from the preset file's directory:

```yaml
post:
  vignettes:
    centered: ../assets/vignettes/centered.png
    top: ../assets/vignettes/top.png
    bottom: ../assets/vignettes/bottom.png
  logo:
    file: ../assets/logos/brand-logo.png

reel_cover:
  black_overlay:
    file: ../assets/overlays/black_9x16.png
  logo:
    file: ../assets/logos/brand-logo.png
  product_name:
    font: ../assets/fonts/product-font.otf
  category_name:
    font: ../assets/fonts/category-font.ttf
```

## GitHub Actions Auto Deploy

The repository includes `.github/workflows/deploy-cpanel.yml`. It deploys automatically whenever `main` is pushed, and it can also be run manually from the GitHub Actions tab.

The workflow deploys code to:

```text
/home/ismails1/framekit
```

Runtime data is kept outside the deployed code at:

```text
/home/ismails1/framekit-data
```

Set these repository secrets before running it:

```text
CPANEL_SSH_HOST=your-server-hostname-or-ip
CPANEL_SSH_USER=your-cpanel-username
CPANEL_SSH_PRIVATE_KEY=the-private-key-used-for-ssh-deploys
```

Optional secrets:

```text
CPANEL_SSH_PORT=22
CPANEL_SSH_KNOWN_HOSTS=known_hosts line for the cPanel server
CPANEL_VENV_PATH=/home/ismails1/virtualenv/framekit/3.13
```

The workflow excludes runtime folders such as `data/`, `input/`, `output/`, `.venv/`, and `.htaccess` from the application-code sync so deploys do not overwrite generated projects or cPanel-managed server config. It then separately syncs bundled presets and deployable brand assets from `data/presets/` and `data/assets/` into `REMOTE_DATA_PATH` without deleting existing runtime uploads. As a compatibility fallback for cPanel environments that still point at the in-app data directory, it also mirrors those bundled presets and assets into `REMOTE_PATH/data/`. It checks SSH connectivity before syncing files so authentication problems are easier to diagnose.

## Smoke Check

After deployment:

1. Open the app URL.
2. Confirm `All In One Edit` loads.
3. Open `Settings` and confirm `Starter Brand` exists.
4. Upload one `3:4` image and one `9:16` image in All In One.
5. Generate the project and download the ZIP.
6. Confirm the ZIP contains:

```text
posts_instagram/
posts_webp_no_vignette/
reel_cover/
```

## Troubleshooting

If the site returns `503 Service Unavailable`, check the cPanel app logs first. Common causes are missing dependencies, missing runtime folders, wrong `FRAMEEDIT_DATA_DIR` permissions, or preset paths pointing at files that do not exist on the server.

If LiteSpeed or Passenger is trying to use an old Python virtualenv, save/update the Python app in cPanel to regenerate the mapping, then reinstall dependencies in the current virtualenv and restart the app by touching `tmp/restart.txt`.
