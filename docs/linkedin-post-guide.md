# LinkedIn Launch Post Guide

Use this guide to publish a polished LinkedIn post for FrameEdit.

## Recommended Image Order

Upload these as a LinkedIn carousel-style image set:

1. `docs/screenshots/03-generated-project.jpg`
   - Purpose: lead with the finished All In One project and ZIP-ready output view.
   - Message: FrameEdit produces organized, ready-to-use assets, not just one-off images.

2. `docs/screenshots/04-grid-mosaic-result.jpg`
   - Purpose: show the Grid Mosaic tab solving profile-tile splitting.
   - Message: one exact-ratio `3240 x 1440` source becomes correctly ordered `1080 x 1440` profile tiles.

3. `docs/screenshots/05-carousel-panorama-result.jpg`
   - Purpose: show the Carousel tab solving panorama slide splitting.
   - Message: the same exact-ratio source becomes three upload-ready portrait carousel slides.

4. `docs/screenshots/02-preview-batch.jpg`
   - Purpose: show the operator review step.
   - Message: previews, vignette choices, and reel-cover selection happen before final generation.

5. `docs/screenshots/01-all-in-one-setup.jpg`
   - Purpose: show how simple the workflow starts.
   - Message: choose a preset, enter product/category text, upload images.

Optional extra images for LinkedIn, if you want to show source/output assets directly:

- `docs/demo-assets/frameedit-showroom-panorama-3240x1440.png`
- `asif-classical-reel-cover.png`
- `asif-classical-post-01.png`
- One generated grid tile
- One generated carousel slide

Those final generated files are runtime outputs, not committed repository assets.

## Suggested LinkedIn Post

I built **FrameEdit**, a local-first image production tool for branded Instagram assets.

The problem was simple but painful: content production kept repeating the same manual design steps:

- resize product photos
- apply the right vignette
- place the logo consistently
- create reel covers with brand typography
- split profile grids without breaking upload order
- split panorama carousels into exact slides
- export PNG/WebP variants
- package everything into folders and ZIPs

FrameEdit turns that into a repeatable browser workflow.

For this demo, I used two source sets:

- a Mahogany Furniture product batch for branded posts and a reel cover
- a generated `3240 x 1440` showroom panorama for Grid Mosaic and Carousel demos

The result:

- `1080 x 1440` Instagram post exports
- a branded `1080 x 1920` reel cover
- no-vignette WebP variants
- correctly ordered profile mosaic tiles
- three upload-ready carousel slides
- organized folders and ZIP downloads

The app is built with Python, Flask, Pillow, HEIC/HEIF support, and YAML-based brand presets. It runs locally, works through a browser UI, and is designed to be cPanel-friendly with no required Node build step.

What I like most about it is that the brand rules are no longer trapped in someone's memory or a manual design file. They are reusable presets.

This is the kind of internal tool that quietly saves hours, reduces mistakes, and makes small content teams feel much bigger.

Repo: https://github.com/hashirjutt13/FrameEdit

#Python #Flask #ImageProcessing #Automation #SocialMediaMarketing #ContentOps #LocalFirst #BuildInPublic

## Shorter Variant

I built **FrameEdit**, a local-first tool that turns product photos and wide source images into branded Instagram posts, reel covers, WebP variants, profile grid mosaics, panorama carousel slides, and ZIP-ready project folders.

It replaces repetitive Canva-style production steps with a repeatable Python + Flask workflow powered by Pillow and YAML brand presets.

For the demo, one Mahogany Furniture batch generated branded post/reel assets, and one exact-ratio `3240 x 1440` showroom image generated both profile grid tiles and a 3-slide carousel.

Repo: https://github.com/hashirjutt13/FrameEdit

#Python #Flask #Automation #ImageProcessing #ContentOps

## Image Captions / Alt Text

Use these if LinkedIn asks for alt text:

1. Generated project page showing FrameEdit output cards, ZIP download, and Instagram grid preview.
2. Grid Mosaic result page showing a `3240 x 1440` source split into three `1080 x 1440` profile tiles with upload order.
3. Carousel result page showing the same `3240 x 1440` source split into three `1080 x 1440` portrait slides.
4. Preview Batch page showing three branded post previews, one reel-cover preview, and vignette selectors.
5. All In One Edit form showing the Mahogany Furniture preset, product name, category name, and upload field.

## Posting Notes

- Lead with `03-generated-project.jpg`; it has the strongest product story.
- Put Grid Mosaic and Carousel screenshots immediately after it to show the app covers more than posts/reel covers.
- Put the GitHub link near the end, not the first line.
- Keep the first two lines punchy so the post does not collapse before the hook.
- If you add final generated asset images, put them after the UI screenshots so people first understand the tool, then see the creative output.
