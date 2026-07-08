# Open Questions

These questions capture choices that may need product input before polishing the tool.

## Current Defaults

The first implementation answers several questions with configurable defaults:

- Input scanning is non-recursive by default; set `scan_recursive: true` to recurse.
- Aspect-ratio tolerance defaults to `0.02` relative tolerance.
- Outputs overwrite by default; set `overwrite: false` to fail when outputs already exist.
- The reel cover output is `reel-cover.png`.
- If multiple `9:16` inputs exist, the first sorted candidate is used and a warning is emitted.
- The WebP no-vignette variant includes the logo by default.
- Product/category text currently comes from `config.yaml`.

## Still Open

1. If recursive scanning is enabled, should output filenames preserve subdirectory structure?
2. Should final brand assets be stored in the repository, ignored locally, or managed as a separate asset pack?
3. Should the CLI expose product/category text overrides, or should they live only in `config.yaml`?
4. Should warnings return success exit codes, or should certain warnings fail CI/batch runs?
5. Are synthetic/generated image fixtures enough, or should there be a small real-world fixture suite?
6. Should a raw original-only WebP mode be supported in addition to the current include-logo option?

## Resolved for Planned Web UI

- cPanel supports Python, so the Web UI should use Flask unless a future hosting constraint changes.
- The Web UI should include an optional simple password gate controlled by environment/config.
- Brand presets should be editable YAML files.
- Output ZIPs should contain grouped folders for `posts_instagram`, `posts_webp_no_vignette`, and `reel_cover`.
- Unsupported image ratios should be rejected in the Web UI.
- Recent project history applies only to All In One jobs.
