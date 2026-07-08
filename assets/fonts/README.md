# Fonts

Place licensed brand font files here when a preset needs custom typography.

Actual font files in this directory are ignored by git so licensed assets do not get committed accidentally.

Example config:

```yaml
reel_cover:
  product_name:
    font: assets/fonts/product-font.otf

  category_name:
    font: assets/fonts/category-font.ttf
```

Leave `font:` blank to use Pillow's default font for local testing.
