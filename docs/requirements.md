# Requirements

This document captures the user-provided project brief for future implementation. It is not an implementation plan by itself.

## Goal

Build a local batch image generator to automate Instagram post and reel-cover creation currently done manually in Canva.

## Recommended Stack

- Python 3
- Pillow
- pillow-heif
- PyYAML
- argparse or Typer

## Inputs

The script receives one input directory and scans all supported images:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`
- `.heic`
- `.heif`

Aspect ratio determines asset type:

- `3:4` -> Instagram post
- `9:16` -> reel cover

Images do not need to already match final export dimensions, but they must closely match the expected aspect ratio. The script should resize them to final output size.

If more than one `9:16` image is found, processing should continue and emit a warning because only one reel cover is expected.

## Post Output

Final size: `1080 x 1440`

Layer order:

1. Original `3:4` image
2. Vignette transparent PNG overlay
3. Logo transparent PNG

Vignette rules:

- Used only for posts.
- Provided as transparent PNG.
- Same size as output: `1080 x 1440`.
- Available options: `centered`, `top`, `bottom`.
- Opacity configurable.

Logo rules:

- Transparent PNG.
- Position uses center coordinates.
- Scale configurable.
- Opacity configurable.

## Post WebP Variant

For every post, also create a WebP version without vignette.

Layer order:

1. Original `3:4` image
2. Logo transparent PNG

Output rules:

- Extension: `.webp`
- Lossless WebP
- Quality: `100`

Assumption from the brief: the WebP variant still includes the logo. If the team wants raw original-only WebP, make that a config option.

## Reel Cover Output

Final size: `1080 x 1920`

Layer order:

1. Original `9:16` image
2. Black overlay image with configurable opacity, default `60%`
3. Logo transparent PNG
4. Product name
5. Category name

Black overlay rules:

- Provided as image.
- Same size as output: `1080 x 1920`.
- Default opacity: `0.60`.
- Configurable.

Text rules:

- Product font default: Migra.
- Category font default: Sloop Script Pro.
- Fonts are provided as `.ttf` or `.otf` files.
- Coordinates use center positioning.
- Font size configurable.
- Color configurable.
- Product name should auto-split into multiple lines.

## Output Structure

```text
output/
  posts_instagram/
    image-name.png

  posts_webp_no_vignette/
    image-name.webp

  reel_cover/
    reel-cover.png
```

## Suggested Config Shape

```yaml
input_dir: input
output_dir: output

supported_extensions:
  - .jpg
  - .jpeg
  - .png
  - .webp
  - .heic
  - .heif

post:
  size: [1080, 1440]
  default_vignette: centered
  vignette_opacity: 1.0

  vignettes:
    centered: assets/vignettes/centered.png
    top: assets/vignettes/top.png
    bottom: assets/vignettes/bottom.png

  logo:
    file: assets/logo.png
    scale: 0.22
    center: [540, 95]
    opacity: 1.0

webp_variant:
  enabled: true
  include_logo: true
  lossless: true
  quality: 100
  method: 6

reel_cover:
  size: [1080, 1920]

  black_overlay:
    file: assets/black_9x16.png
    opacity: 0.60

  logo:
    file: assets/logo.png
    scale: 0.20
    center: [540, 360]
    opacity: 1.0

  product_name:
    text: "ECLAT CONSOLE"
    font: assets/fonts/Migra.otf
    size: 92
    center: [540, 940]
    color: "#f4efe6"
    auto_multiline: true
    max_width: 720
    line_spacing: 1.05

  category_name:
    text: "Consoles"
    font: assets/fonts/SloopScriptPro.otf
    size: 82
    center: [540, 1580]
    color: "#f4efe6"
```

## Acceptance Criteria

- `3:4` images generate Instagram post PNGs.
- `3:4` images also generate no-vignette lossless WebP variants.
- `9:16` image generates one reel cover.
- Transparent logo overlays correctly.
- Vignette appears only on post PNGs.
- Black overlay appears only on reel cover.
- HEIC/HEIF files can be read.
- Font, size, opacity, logo scale, and coordinates are editable from config.
- Multiple `9:16` inputs trigger a warning.
- Output images match exact required dimensions.

