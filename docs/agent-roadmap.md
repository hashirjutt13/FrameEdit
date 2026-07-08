# Agent Roadmap

This roadmap is a future implementation guide. It exists so agents can pick up work in clean, testable slices.

## Phase 0: Project Setup

Do this only after the user asks to start implementation.

- Choose CLI library: `argparse` for minimal dependencies or Typer for richer UX.
- Add Python project metadata.
- Add dependency management.
- Add formatter/linter/test configuration.
- Add placeholder sample config only if the user wants repository-tracked examples.

Verification gate:

- Dependency install works in a clean environment.
- CLI help command works.

## Phase 1: Config and Validation

- Load YAML config.
- Resolve paths relative to the config file.
- Validate required sections.
- Validate asset existence.
- Validate overlay dimensions once image loading exists.
- Validate numeric fields such as opacity, scale, size, and coordinates.

Verification gate:

- Unit tests cover valid config and missing required fields.
- Errors are actionable and include the config path/key.

## Phase 2: Input Discovery and Classification

- Register HEIF support at startup.
- Scan supported extensions.
- Apply EXIF orientation correction before dimension checks.
- Classify images by aspect-ratio tolerance.
- Warn for unsupported ratios.
- Warn when more than one reel-cover candidate is found.
- Warn when no reel-cover candidate is found.

Verification gate:

- Tests cover `3:4`, `9:16`, unsupported ratios, multiple reel candidates, and case-insensitive extensions.

## Phase 3: Shared Image Composition Primitives

- Resize/crop to target dimensions.
- Scale transparent logo by configured scale.
- Place overlays and logos by center coordinates.
- Apply configurable opacity to RGBA layers.
- Save exact output dimensions.

Verification gate:

- Tests or generated fixture checks prove output dimensions and layer placement.

## Phase 4: Post Generation

- Generate `posts_instagram/*.png`.
- Composite original image, selected vignette, and logo.
- Generate `posts_webp_no_vignette/*.webp`.
- Respect WebP settings: lossless, quality, method, include-logo option.

Verification gate:

- Fixtures verify PNG and WebP outputs exist with expected dimensions.
- Vignette is excluded from WebP variant.

## Phase 5: Reel Cover Generation

- Composite original image, black overlay, logo, product name, and category name.
- Load configured `.ttf` or `.otf` fonts.
- Center text blocks by configured coordinates.
- Auto-wrap product name within configured max width.
- Respect line spacing and color.

Verification gate:

- Fixture verifies output dimensions.
- Text rendering works with provided font files.
- Product title wraps within max width.

## Phase 6: Dry Run and Operator UX

- Add `--dry-run`.
- Print planned outputs and warnings without writing files.
- Return useful exit codes for validation failure.
- Keep normal generation quiet but informative.

Verification gate:

- Dry run creates no output files.
- Validation failures return non-zero exit status.

## Suggested Work Allocation

- Agent A: project setup, CLI shell, config loading.
- Agent B: image discovery, HEIF registration, aspect-ratio classification.
- Agent C: composition helpers and overlay/logo placement.
- Agent D: post and WebP generation.
- Agent E: reel-cover text rendering and wrapping.
- Agent F: end-to-end fixtures, docs, and packaging polish.

