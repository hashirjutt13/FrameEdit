# Web UI Agentic Workflow

This workflow is for agents building the Flask Web UI in controlled slices. It assumes the current CLI generator already works and must remain usable.

## Prime Directive

Do not rewrite the generator as a separate Web UI script.

Agents should refactor toward shared services inside `src/frameedit/`, then let the Flask app call those services. The CLI and Web UI must use the same generation behavior.

## Required Reading

Before implementation, read:

- `AGENTS.md`
- `docs/requirements.md`
- `docs/decisions.md`
- `docs/open-questions.md`
- `docs/web-ui-requirements.md`
- `docs/web-ui-agentic-workflow.md`

## Start Conditions

Start implementation only after the user explicitly asks for it.

Before editing:

1. Run `git status --short --branch`.
2. Confirm whether the user wants a branch. Recommended branch name: `web-ui`.
3. Run the current test suite.
4. Run a CLI smoke test if sample images are available.
5. Record any pre-existing failures before making changes.

## Suggested Target Structure

Use this as a guide, not a rigid mandate:

```text
src/frameedit/
  config.py
  image_ops.py
  pipeline.py
  render.py
  web_services/
    presets.py
    assets.py
    projects.py
    previews.py
    zipfiles.py

web_app/
  app.py
  routes/
    all_in_one.py
    posts.py
    reel_cover.py
    settings.py
    recent.py
    auth.py
  templates/
  static/

data/
  presets/
  assets/
    logos/
    fonts/
    vignettes/
  projects/
  temp/
```

Avoid committing user-uploaded assets, generated outputs, project uploads, or ZIP files unless the user specifically asks.

## Work Slices

Each slice should leave the app in a coherent state and include focused verification.

### Slice 0: Baseline Safety

Goal: protect the working CLI and establish the implementation branch.

Tasks:

- Capture `git status`.
- Run tests.
- Run the current generator against the known sample directory if available.
- Add or update docs only if needed.

Gate:

- Baseline test result is recorded.
- No functional behavior is changed.

### Slice 1: Shared Service Contracts

Goal: expose generation behavior through callable services without changing CLI behavior.

Tasks:

- Identify CLI-only assumptions in `pipeline.py` and `cli.py`.
- Add service functions for classification, generation, and output naming.
- Keep `generate.py` and `frameedit` CLI behavior stable.
- Add tests around service functions.

Gate:

- Existing CLI tests pass.
- New service tests pass.
- CLI smoke output still matches expected dimensions and folders.

### Slice 2: Preset Storage

Goal: support file-based brand presets.

Tasks:

- Add preset load/save/list/duplicate/rename/delete services.
- Create a migration/helper that can make the default `Starter Brand` preset from current `config.yaml`.
- Validate preset assets and numeric fields.
- Keep config path resolution predictable.

Gate:

- Tests cover valid presets, missing assets, invalid YAML, duplicate names, and slug generation.
- Default preset maps to current Starter Brand config values.

### Slice 3: Asset Library

Goal: manage uploaded logos, fonts, and vignettes.

Tasks:

- Add asset storage conventions under `data/assets/`.
- Sanitize upload filenames.
- Preserve original file extensions.
- Validate allowed asset types.
- Let presets reference existing assets.

Gate:

- Tests cover allowed/disallowed asset uploads and path traversal protection.
- Current logo/fonts/vignettes are usable by the default preset.

### Slice 4: Project and ZIP Services

Goal: create saved All In One project folders and ZIPs.

Tasks:

- Add product and brand slug helpers.
- Add project folder creation.
- Add `project.yaml` metadata.
- Add ZIP packaging with required folder structure.
- Add recent-project indexing by filesystem scan or metadata files.

Gate:

- Tests cover project paths, duplicate project names, ZIP contents, and metadata loading.

### Slice 5: Flask Skeleton

Goal: add the cPanel-friendly Web UI shell.

Tasks:

- Add Flask dependency.
- Add `web_app/app.py`.
- Add base template and navigation.
- Add basic pages for All In One, Posts Edit, Reel Cover Edit, Recent Projects, and Settings.
- Add static CSS without a frontend build step.

Gate:

- Flask app imports successfully.
- Basic route tests pass.
- CLI still works.

### Slice 6: Upload and Preview Flow

Goal: let users upload images and see validation results.

Tasks:

- Add upload handling for multiple images.
- Support HEIC/HEIF.
- Classify `3:4` and `9:16` images.
- Reject unsupported files and ratios with visible messages.
- Generate temporary previews without saving Recent Project records.

Gate:

- Tests cover post, reel-cover, unsupported image, no reel candidate, and multiple reel candidates.
- Manual browser check confirms previews render.

### Slice 7: All In One Edit

Goal: complete the primary workflow.

Tasks:

- Select brand preset.
- Enter product/category text.
- Upload images.
- Choose reel cover when multiple `9:16` images exist.
- Choose vignette per post image.
- Generate final outputs.
- Save project permanently.
- Download individual files and ZIP.

Gate:

- End-to-end test or manual smoke confirms full folder and ZIP output.
- Recent Projects includes the saved job.

### Slice 8: Posts Edit

Goal: generate posts only.

Tasks:

- Accept only `3:4` uploads.
- Select brand preset.
- Choose vignette per image.
- Preview outputs.
- Download individual files or ZIP.
- Avoid saving to Recent Projects.

Gate:

- Tests or manual smoke confirm no recent-project record is created.

### Slice 9: Reel Cover Edit

Goal: generate reel cover only.

Tasks:

- Accept one `9:16` upload.
- Select brand preset.
- Enter product/category text.
- Preview output.
- Download image.
- Avoid saving to Recent Projects.

Gate:

- Tests or manual smoke confirm output dimensions and no recent-project record.

### Slice 10: Settings UI

Goal: make brand presets and assets editable from the UI.

Tasks:

- Build preset list/detail forms.
- Support create, edit, duplicate, rename, delete.
- Build asset upload/list controls.
- Expose numeric controls for positions, scales, sizes, opacity, blur, line spacing, and tracking.
- Expose vignette choices for `center`, `top`, and `bottom`.

Gate:

- Form submissions validate and preserve YAML correctly.
- Editing a preset changes subsequent previews/generation.

### Slice 11: Recent Projects

Goal: make saved All In One work discoverable.

Tasks:

- Show saved projects.
- Search/filter by brand and product name.
- Open a project detail page.
- Download existing ZIP again.
- View individual generated outputs.

Gate:

- Tests cover filtering.
- Manual check confirms old saved projects remain accessible after app restart.

### Slice 12: Optional Password Gate

Goal: add lightweight protection without complicating deployment.

Tasks:

- Read `WEB_UI_PASSWORD` from environment.
- If empty, bypass login.
- If set, require a session login.
- Add logout.
- Protect all app pages and downloads.

Gate:

- Tests cover disabled auth, failed login, successful login, and protected download route.

### Slice 13: cPanel Deployment Package

Goal: prepare the app for hosting.

Tasks:

- Document cPanel Python App setup.
- Add WSGI/passenger entrypoint if needed.
- Document environment variables.
- Document writable directories.
- Confirm dependencies in `pyproject.toml`.
- Add a production smoke checklist.

Gate:

- Fresh environment install works.
- Flask app imports from the cPanel-style entrypoint.
- Required writable folders can be created automatically.

## Suggested Agent Roles

Use these roles if multiple agents are working in parallel.

- Architecture agent: shared service boundaries, preset schema, path conventions.
- Backend agent: Flask routes, upload handling, generation orchestration.
- UI agent: templates, CSS, preview pages, settings forms.
- QA agent: tests, smoke cases, ZIP inspection, visual sanity checks.
- Deployment agent: cPanel notes, WSGI entrypoint, environment setup.

Parallel work is safest after Slice 2 defines preset contracts and Slice 4 defines project storage contracts.

## Handoff Template

Each agent should leave a short handoff note:

```text
Completed:
- ...

Changed files:
- ...

Verification:
- ...

Known issues:
- ...

Next recommended slice:
- ...
```

## Review Checklist

Before merging or calling a slice complete:

- Existing CLI still works.
- Existing tests pass.
- New behavior has focused tests.
- User assets and outputs are not committed accidentally.
- Generated dimensions remain exact.
- Paths are sanitized for uploads and downloads.
- Settings are stored in YAML, not hard-coded in routes/templates.
- Web UI can run without internet access.
- cPanel constraints are respected.

## Definition of Done for the Web UI

The Web UI is complete when:

- `Starter Brand` exists as the default preset with current visual settings.
- All In One can upload, preview, vignette-adjust, generate, save, and ZIP a full product batch.
- Posts Edit and Reel Cover Edit work as one-off tools.
- Settings can manage presets and assets.
- Recent Projects can search/filter saved All In One jobs.
- Optional password protection works.
- The app is documented for cPanel deployment.
- The CLI remains available and tested.
