# Web UI Requirements

This document captures the agreed requirements for the Flask Web UI. It is a product and technical contract for future implementation, not an implementation by itself.

## Goal

Build a cPanel-friendly Web UI around the existing Instagram post and reel-cover generator.

The Web UI should let the user upload images, choose a brand preset, enter product/category text, preview generated assets, change per-image vignette choices, download individual files or a ZIP, and manage reusable brand settings.

## Architecture Decision

Keep one repository and one shared generation engine.

- Keep `generate.py` and the CLI usable.
- Keep image generation logic in `src/frameedit/`.
- Add a Flask web layer that calls shared service functions.
- Do not fork the current script into a separate Web UI implementation.

## Recommended Stack

- Backend: Flask
- Templates: Jinja2
- Styling: plain CSS, no required frontend build step
- Storage: local filesystem
- Presets: YAML files
- Image processing: existing Pillow and `pillow-heif` pipeline
- Deployment: cPanel Python App / Passenger

## Users and Auth

- Primary users: the owner and maybe one additional person.
- Add a simple optional password gate.
- If `WEB_UI_PASSWORD` is empty or absent, auth is disabled.
- If `WEB_UI_PASSWORD` is set, require login before accessing the UI.

## Brand Presets

The Web UI must support multiple editable brand presets. The default preset is `Starter Brand`, generated from the current working `config.yaml` and current asset paths.

Each preset should be stored as a YAML file, for example:

```text
data/presets/starter-brand.yaml
```

Each preset should store:

- Brand name and slug
- Logo asset path
- Post logo position, scale, and opacity
- Reel-cover logo position, scale, and opacity
- Product-name font, size, color, center, tracking, line spacing, max width, multiline behavior, and last-word line-break behavior
- Category-name font, size, color, center, and line spacing
- Reel-cover background blur settings
- Black overlay settings
- Post vignette assets for `center`, `top`, and `bottom`
- Default post vignette
- Canvas sizes
- WebP settings
- Supported extensions and aspect-ratio tolerance, unless those remain global

Preset management must support:

- Create
- Edit
- Duplicate
- Rename
- Delete

## Asset Library

The Web UI must support uploaded reusable assets:

- Logos
- Fonts
- Vignettes

Assets should live under local filesystem storage, for example:

```text
data/assets/
  logos/
  fonts/
  vignettes/
```

The current logo, fonts, and vignettes should be available to the default `Starter Brand` preset.

## Image Classification

Uploaded files are classified by aspect ratio after image metadata and orientation are handled.

- `3:4` images are posts.
- `9:16` images are reel-cover candidates.
- Unsupported files or unsupported ratios must be rejected and shown to the user.
- HEIC and HEIF must be supported.
- Videos are unsupported.

For All In One generation:

- If no `9:16` image is found, warn the user.
- If more than one `9:16` image is found, warn the user and let them choose which image becomes the reel cover.

## Main Pages

### All In One Edit

Purpose: generate a full batch for one product.

Required inputs:

- Brand preset
- Product name
- Category name
- Multiple uploaded images

Required behavior:

- Detect post images and reel-cover candidates automatically.
- Reject unsupported files/ratios.
- Show previews before final download.
- Let the user choose `center`, `top`, or `bottom` vignette per post image.
- Let the user download individual generated files.
- Let the user download all generated files as a ZIP.
- Save each final All In One project permanently.
- Show saved projects through a Previous Work option on the All In One screen.

### Posts Edit

Purpose: generate only post assets.

Required behavior:

- Upload one or more post images.
- Accept only `3:4` images.
- Select brand preset.
- Preview generated outputs.
- Let the user choose `center`, `top`, or `bottom` vignette per image.
- Download individual files or a ZIP.
- Do not add these jobs to Recent Projects.

### Carousel Panorama

Purpose: split one wide source image into a single Instagram carousel where each slide continues the same horizontal scene.

Required behavior:

- Upload one horizontal source image.
- Choose a carousel name.
- Choose a slide count from 2 to 20.
- Default to `3:4` portrait slides at `1080 x 1440`.
- Also support `4:5` portrait slides at `1080 x 1350` and square slides at `1080 x 1080`.
- Show the recommended source canvas size and simplified source-image ratio based on the selected slide count and slide format.
- Reject source images that do not match the recommended source ratio for the selected slide count and format.
- Export PNG slides in left-to-right upload order.
- Download individual slide files or a ZIP.
- Save generated carousels permanently in a dedicated Recent Carousels list.
- Let the user open, ZIP-download, or delete any saved carousel.

### Reel Cover Edit

Purpose: generate only a reel cover.

Required behavior:

- Upload one `9:16` image.
- Select brand preset.
- Enter product name and category name.
- Preview generated output.
- Download the generated reel cover.
- Do not add these jobs to Recent Projects.

### All In One Previous Work

Purpose: browse saved All In One projects.

Required behavior:

- Be reachable from the All In One screen, not as a separate top-level navigation tab.
- Show only All In One projects.
- Search and filter by brand and product name.
- Open a saved project.
- Download the ZIP again.
- View individual generated files.

### Settings

Purpose: manage presets and assets.

Required behavior:

- Manage brand presets.
- Upload and reuse logos, fonts, and vignettes.
- Configure all current generation settings.
- Use numeric inputs for positioning and sizing.
- Drag-and-drop positioning is not required for the first Web UI version.

## Output Naming

Use product-name based filenames.

Example for product name `ECLAT CONSOLE` and brand `Starter Brand`:

```text
eclat-console-post-01.png
eclat-console-post-01.webp
eclat-console-reel-cover.png
```

## Saved Project Structure

All In One projects should be saved permanently in dated folders.

Example:

```text
data/projects/starter-brand/2026-07-05-eclat-console/
  uploads/
  posts_instagram/
    eclat-console-post-01.png
  posts_webp_no_vignette/
    eclat-console-post-01.webp
  reel_cover/
    eclat-console-reel-cover.png
  eclat-console-starter-brand.zip
  project.yaml
```

## ZIP Structure

The downloaded ZIP should contain grouped output folders.

Example:

```text
eclat-console-starter-brand/
  posts_instagram/
    eclat-console-post-01.png
  posts_webp_no_vignette/
    eclat-console-post-01.webp
  reel_cover/
    eclat-console-reel-cover.png
```

## Validation Rules

- Reject unsupported extensions.
- Reject unsupported aspect ratios.
- Reject missing preset assets.
- Reject missing product/category text when generating reel covers.
- Warn on no reel-cover candidate in All In One.
- Warn on multiple reel-cover candidates in All In One and require a selection.
- Do not silently fall back to different fonts or logos.

## Deployment Requirements

- Must be deployable on cPanel with Python support.
- Avoid a required Node build step.
- Runtime should not depend on internet access.
- Store uploads, assets, presets, generated outputs, and project records on the filesystem.
- Include deployment notes before final handoff.

## Acceptance Criteria

- Existing CLI still works.
- Existing tests still pass.
- Web UI can generate the same visual outputs as the current CLI defaults.
- Default Starter Brand preset matches the current working config.
- User can create and edit another brand preset without changing code.
- All In One can generate previews, individual downloads, and ZIP downloads.
- Posts Edit and Reel Cover Edit can generate one-off outputs without recording recent projects.
- All In One Previous Work can search/filter saved All In One projects by brand and product name.
- Optional password gate works when enabled and stays disabled when no password is configured.
