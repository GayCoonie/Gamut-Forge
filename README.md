# Gamut Forge

A static, client-side image quantizer for arbitrary fixed palettes—including palettes larger than 256 colors.

## What it does

- Exact nearest-neighbor matching in OKLab using a balanced k-d tree
- Optional serpentine Floyd–Steinberg dithering in linear-light RGB
- Imports GIMP `.gpl`, hex text, JSON containing hex colors, and flat-color palette images
- Includes eleven 1024-color palettes: three structured HCT-style profiles, Maximum Coverage 48, six retro/curated/RGB9-derived profiles, and a literal 10×10×10 encoded-sRGB cube with 24 supplemental grays
- Preserves transparency and exports an RGBA PNG
- Reports used colors, mean and maximum OKLab error, processing time, and palette conformance

Everything runs in the browser. No image or palette is uploaded.

## GitHub Pages

The publishable site is the `dist/` directory. Either configure Pages to publish that directory through the included Actions workflow, or copy its contents to the root of a `gh-pages` branch.

1. Create a GitHub repository and add these files.
2. In **Settings → Pages**, choose **GitHub Actions** as the source.
3. Push to `main`; the included workflow deploys `dist/`.

## Local use

Serve the repository with any static file server and open it in a browser. For example:

```sh
python3 -m http.server 8080 -d dist
```

Opening `index.html` directly may prevent the Web Worker from loading in some browsers, so use a local server.

## Methodological note

OKLab Euclidean distance is a good practical compromise for palette matching, but it is not a full appearance model. Error diffusion can improve perceived gradients while increasing direct per-pixel error. This app therefore reports direct OKLab error and leaves dithering optional.

The **RGB9 retro fusion** profile fixes the complete RGB333/RGB9, RGB332, and RGB222 machine palettes. Their 832 nominal entries collapse to 688 distinct sRGB colors where the systems overlap. Its remaining 336 slots are weighted farthest-point selections in OKLab from a deduplicated union of RGB444, web-safe colors, and the X Consortium's 1994 `rgb.txt`. No unrestricted RGB color can enter this profile.

The **Retro artist wheel** profile replaces the web-safe cube in an RGB333 + RGB332 + RGB233 + RGB222 + Windows-16 construction. Those historical systems contribute 816 unique anchors. Its artist vocabulary begins with 60 supplied colors, extends their five HSV signatures across 12 interstitial hues, and pairs the resulting 120 colors with 120 darker companions (`S × 0.75`, `V × 0.55`). All 120 core colors and the 94 most perceptually useful companions are retained, contributing exactly 208 new colors and bringing the palette to 1,024.

The **Lospec 19 max-fit** profile contains only verbatim colors from 19 supplied low-spec palettes. Their 1,487 entries collapse to 1,420 unique RGB colors. Eight RGB corners are fixed, then weighted farthest-point sampling in OKLab retains the 1,016 strongest remaining colors. The 396 omitted candidates are all represented by close retained neighbors; the worst omission is about 0.0186 ΔEOK away.

## License

MIT
