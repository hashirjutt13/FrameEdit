# Agent Instructions

## Current State

This repository contains FrameEdit: a local-first image production toolkit for branded Instagram posts, reel covers, profile mosaics, and panorama carousels.

The CLI and Flask Web UI are both implemented and should continue sharing the same generation services.

The tracked starter assets are placeholders. Brand-specific logos, fonts, uploaded assets, input images, generated outputs, and ZIP files should stay local or live in runtime storage.

## Project Summary

Build and maintain a local Python image generator that automates Instagram post, reel-cover, mosaic, and carousel production currently done manually in design tools.

The tool should:

- Scan an input directory for supported images.
- Treat close `3:4` images as Instagram posts.
- Treat close `9:16` images as reel-cover inputs.
- Generate exact-size PNG and WebP outputs.
- Composite configured logo, vignette, black overlay, and text layers.
- Optionally blur the fitted reel-cover background before overlays/text.
- Read settings from a YAML config.
- Support HEIC/HEIF through `pillow-heif`.
- Provide dry-run validation.
- Eventually support a Flask Web UI that reuses the same generation engine and stores editable brand presets as YAML files.

## Required Reading Before Changes

Before changing code in this repository, read:

- `docs/requirements.md`
- `docs/agent-roadmap.md`
- `docs/open-questions.md`
- `docs/decisions.md`

Before changing Web UI related code, also read:

- `docs/web-ui-requirements.md`
- `docs/web-ui-agentic-workflow.md`

## Current Implementation Shape

- CLI wrapper: `generate.py`
- Package: `src/frameedit/`
- Config: `config.yaml`
- Placeholder asset generator: `tools/create_placeholder_assets.py`
- Tests: `tests/`
- Planned Web UI: Flask app under `web_app/`, with reusable services kept in or near `src/frameedit/`.

Use:

```bash
.venv/bin/python generate.py --config config.yaml --dry-run
.venv/bin/python generate.py --config config.yaml
.venv/bin/python -m pytest
```

## Development Guardrails

- Keep implementation local-first and deterministic.
- Prefer small, reviewable changes over broad rewrites.
- Do not commit user-provided brand assets, inputs, or generated outputs by accident.
- Preserve generated output dimensions exactly:
  - Posts: `1080 x 1440`
  - Reel covers: `1080 x 1920`
- Keep image-processing behavior configurable through YAML rather than hard-coded values where requirements call for configuration.
- Validate missing files, overlay size mismatch, unsupported ratios, no reel cover, and multiple reel-cover candidates.
- Avoid network dependencies in the runtime path.
- Keep the CLI and Web UI backed by shared generation services.
- Store Web UI presets as YAML files and uploaded assets/projects on the local filesystem.
- Keep Web UI implementation cPanel-friendly: no mandatory Node build step and no internet dependency at runtime.

## Suggested Verification

Keep checks for:

- Config loading and validation.
- Aspect-ratio classification tolerance.
- Resize/crop output dimensions.
- Logo scaling and center-coordinate placement.
- Overlay opacity compositing.
- Product-name multiline wrapping.
- Dry-run behavior.
- Warning behavior for multiple `9:16` images.
- CLI smoke behavior after meaningful changes.
- Web UI route/import smoke checks once Flask is added.
- Preset, asset, upload, ZIP, auth, and recent-project behavior once those features exist.

## Git Hygiene

- Work from `main` unless the user asks for a branch.
- Check `git status --short` before editing.
- Do not revert unrelated user changes.
- Keep user-provided brand assets, inputs, and generated outputs out of git unless the user asks otherwise.
