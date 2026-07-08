# Decision Log

Record meaningful implementation decisions here. Keep entries short and dated.

## 2026-07-04: Pre-Implementation Repository Prep

- Initialized this directory as a git repository on `main`.
- Added agent-facing project documentation.
- Added ignore rules for local inputs, generated outputs, Python caches, virtual environments, and user-provided assets.
- No application implementation was started.

## 2026-07-04: Initial Implementation

- Used `argparse` for the CLI to keep runtime dependencies minimal.
- Added a Python package under `src/frameedit/` plus the root `generate.py` wrapper.
- Added `config.yaml` as the editable local configuration.
- Defaulted scanning to non-recursive, with `scan_recursive` available in config.
- Defaulted aspect-ratio matching to `0.02` relative tolerance.
- Defaulted output overwrite behavior to `true`, with `overwrite` available in config.
- Kept the WebP variant logo enabled by default through `webp_variant.include_logo`.
- When multiple `9:16` images are found, the batch warns and uses the first candidate for `reel-cover.png`.
- Generated local placeholder vignette, black overlay, and logo assets instead of downloading third-party images.
- Initially left reel-cover font paths blank so the tool could run before brand fonts were provided.

## 2026-07-04: Reel-Cover Font Paths

- Reel-cover text can use configured `.otf` or `.ttf` files.
- Kept actual font files ignored by git because they may be licensed brand assets.
- Public starter config leaves font paths blank so the project can run out of the box.

## 2026-07-05: Logo and Reel-Cover Styling

- Configured both post and reel-cover outputs to use the configured brand logo asset.
- Set reel-cover product font size to `86`.
- Set reel-cover category font size to `90`.
- Added `reel_cover.background_blur` and enabled it at `0.15` intensity, mapped to a Gaussian blur radius through `max_radius`.
- Applied reel-cover blur to the fitted background photo before black overlay, logo, and text so foreground branding remains sharp.

## 2026-07-05: Product Title Tracking and Line Break

- Added configurable text `letter_spacing`, interpreted as tracking units where `1000` equals `1em`.
- Set reel-cover product title tracking to `150`.
- Added `last_word_second_line` and enabled it for the reel-cover product title so the final word is forced onto the second line.

## 2026-07-05: Initial Reel-Cover Visual Tuning

- Initially increased reel-cover product font size from `86` to `118` to better match the apparent Canva scale before extracting the PDF reference.
- Increased product title line spacing from `1.05` to `1.18`.
- Reduced reel-cover background blur intensity from `0.15` to `0.06`.

## 2026-07-05: PDF-Extracted Reel-Cover Positions

- Extracted layout measurements from a reel-cover reference export.
- The PDF page is `810 x 1440 pt`, so positions map to `1080 x 1920 px` with a `4/3` scale.
- Set reel-cover logo center to `[540, 330]` and scale to `0.229`, matching a reference width of about `247px`.
- Set reel-cover product title center to `[540, 955]`.
- Set reel-cover category center to `[540, 1681]`.
- Set product and category text color to `#e1d9cb`.
- Set product size to `115` and category size to `120` based on the scaled PDF text boxes.

## 2026-07-05: Post Logo Position

- Extracted post logo placement from reference post exports.
- Across 142 detected `1080 x 1440` Canva post exports, the logo box was consistently about `216 x 53px`.
- Set post logo center to `[540, 100]`.
- Set post logo scale to `0.228`; this compensates for transparent padding in the logo asset and produces a visible gold logo box of about `216 x 53px`.

## 2026-07-05: Web UI Requirements and Workflow

- Chose Flask for the future Web UI because cPanel Python support is available and the current generator is already Python.
- Decided to keep the current CLI and Web UI in one repository with a shared generation engine, rather than maintaining a separate Web UI copy.
- Decided that brand presets should be file-based YAML, with `Starter Brand` as the default preset derived from the current config and assets.
- Decided that All In One jobs should be saved permanently as dated project folders, while Posts Edit and Reel Cover Edit should remain one-off tools.
- Decided that the first Web UI version only needs numeric positioning controls and three per-image vignette choices: `center`, `top`, and `bottom`.

## 2026-07-08: Grid Mosaic 3x1 Splitter

- Added a Web UI Grid Mosaic tab for a 3-column, 1-row profile mosaic from one horizontal source image.
- Added a `3:4` profile-native format that uses a `3240 x 1440` source canvas and exports three `1080 x 1440` PNG posts with no bleed or color fill.
- Kept the existing `4:5` feed-safe format with a `3106 x 1350` bleed source canvas so the three `1080 x 1350` PNG posts can be cropped without any blank edge fill.
- Named outputs in reverse upload order so the profile grid shows the mosaic left-to-right after posting.

## 2026-07-08: Carousel Panorama Splitter

- Added a Web UI Carousel tab for splitting one wide source image into left-to-right carousel slides.
- Defaulted carousel slides to `3:4` at `1080 x 1440`, matching the current project post size and newer Instagram support for `3:4` feed/carousel photos.
- Also supported `4:5` at `1080 x 1350` and square `1:1` at `1080 x 1080`.
- Limited slide count to Instagram's carousel item range of 2 to 20.
- Saved outputs under `carousel_panorama/` and kept upload order left-to-right because carousel swiping uses the selected file order, unlike profile-grid mosaic posting.
- Required the carousel source image to be horizontal so portrait/square uploads fail with an actionable validation message.
- Added a live Web UI hint for ideal source canvas and simplified source ratio because these change with slide count and slide format.
- Rejected carousel source images whose aspect ratio does not exactly match the selected slide count and slide format.

## 2026-07-08: Carousel History

- Saved Web UI carousel jobs permanently under `data/carousels/` with uploaded source files, slide outputs, ZIP archives, and `carousel.yaml` metadata.
- Kept carousel history separate from All In One Recent Projects.
- Added Recent Carousels listing, detail, ZIP download, individual slide download, and delete actions.

## 2026-07-08: FrameEdit Web UI Branding

- Branded the browser-facing Web UI as `FrameEdit`, separate from the Starter Brand preset and assets.
- Kept the internal Python package, CLI command, YAML presets, and storage paths under the existing `frameedit` naming.
- Added deterministic SVG logo concepts plus active SVG/PNG/ICO favicon assets under `web_app/static/brand/`.

## 2026-07-08: All In One Previous Work

- Removed the separate Recent Projects top-level navigation tab.
- Kept saved All In One project history accessible through a Previous Work action on the All In One screen.
- Kept project detail and previous-work pages grouped under the All In One navigation state.

## 2026-07-08: Vercel-Inspired Web UI Restyle

- Restyled the Flask Web UI with a Vercel/Geist-inspired design system.
- Mapped the UI to near-white canvas, near-black ink, grey text tiers, blue focus/link states, hairline cards, compact app buttons, and minimal depth.
- Kept the implementation buildless and cPanel-friendly by using CSS variables and local font fallbacks instead of adding a frontend build step or remote font dependency.

## 2026-07-08: Preset JSON Import and Local Asset Seeding

- Added a Settings import path that accepts preset/config settings as JSON, validates them through the shared preset loader, and saves them back as YAML presets.
- Added local logo/font seeding into ignored `data/assets/` storage so project logos and brand fonts can be made available to the Web UI without committing user assets.

## 2026-07-08: Deployable Mahogany Brand Assets

- Made `data/assets/logos/` and `data/assets/fonts/` deployable through git so selected brand assets appear on the hosted Web UI after deployment.
- Added a `Mahogany Furniture` preset that references tracked Mahogany logo, Migra product font, and Sloop category font assets.
- Updated the cPanel workflow to sync bundled presets, logos, fonts, vignettes, and overlays into runtime data without deleting existing uploads or projects.
- Updated the Passenger entrypoint to default to the sibling `framekit-data` runtime directory when cPanel does not set `FRAMEEDIT_DATA_DIR`.
