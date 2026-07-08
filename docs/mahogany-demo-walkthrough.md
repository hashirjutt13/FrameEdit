# Mahogany Furniture Demo Walkthrough

This walkthrough shows FrameEdit running a real local product batch with the Mahogany Furniture preset.

The demo uses one reel-cover image and three supported `3:4` product photos from an Asif Classical furniture batch. FrameEdit classifies the inputs, renders branded post assets, creates a reel cover, builds WebP variants, and saves a ZIP-ready project.

## 1. Start The Batch

Choose the brand preset, enter the product/category text, and upload the product images.

![All In One setup](screenshots/01-all-in-one-setup.jpg)

For this demo:

- Brand preset: `Mahogany Furniture`
- Product name: `ASIF CLASSICAL`
- Category name: `Bedroom Sets`
- Source images: three `3:4` post photos and one `9:16` reel-cover image

## 2. Preview Before Generating

FrameEdit previews the post and reel-cover outputs before writing the final project. Each post can use a center, top, or bottom vignette.

![Preview batch](screenshots/02-preview-batch.jpg)

This step is where a content operator can catch the common manual-production mistakes:

- Wrong image ratio
- Wrong reel-cover candidate
- Incorrect vignette position
- Missing brand/logo layer
- Product/category text issues

## 3. Generate The Saved Project

After preview, FrameEdit saves a permanent project with grouped outputs and a ZIP download.

![Generated project](screenshots/03-generated-project.jpg)

The saved project contains:

```text
posts_instagram/
  asif-classical-post-01.png
  asif-classical-post-02.png
  asif-classical-post-03.png

posts_webp_no_vignette/
  asif-classical-post-01.webp
  asif-classical-post-02.webp
  asif-classical-post-03.webp

reel_cover/
  asif-classical-reel-cover.png

asif-classical-mahogany-furniture.zip
project.yaml
```

FrameEdit also shows an Instagram Grid Preview so the operator can check how post and reel-cover tiles sit together in a profile row.

## Why This Matters

The demo replaces a repetitive design workflow with a repeatable production process:

- Product photos become exact-size Instagram post exports.
- Reel covers use consistent brand typography, overlay, blur, and logo placement.
- WebP variants are created automatically.
- Final files are grouped, named, and zipped without manual folder cleanup.
- The same engine supports both CLI and Web UI workflows.
