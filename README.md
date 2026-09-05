# Gamut Forge

A static, client-side image quantizer for arbitrary fixed palettes—including palettes larger than 256 colors.

## What it does

- Two selectable exact matching engines: fast OKLab k-d tree and CIEDE2000
- Optional serpentine Floyd–Steinberg dithering in linear-light RGB
- Imports GIMP `.gpl`, hex text, JSON containing hex colors, and flat-color palette images
- Includes thirteen 1024-color palettes plus a 4096-color retro source union assembled from 29 supplied artist/game palettes, historical hardware and software palettes, low-bit RGB arrangements, and deweighted X11 colors
- Preserves transparency and exports an RGBA PNG
- Reports used colors, mean and maximum error in the chosen metric, processing time, and palette conformance
- Cancelable processing and downloadable TXT/GPL/KPL/JSON exports of the distance-first 1024 profile

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

OKLab Euclidean distance is a good practical compromise for palette matching, but it is not a full appearance model. The additional CIEDE2000 engine instead minimizes ΔE00 in CIELAB D65 (2° observer, kL = kC = kH = 1). Both decode sRGB into linear light as an intermediate step, then apply nonlinear perceptual transforms; neither minimizes linear-RGB distance. CIEDE2000 is not assumed universally better—compare the two on the intended pixel art.

CIEDE2000 matching is exact, not an OKLab/CIELAB shortlist approximation. The OKLab neighbor supplies an initial upper bound. Every other palette entry is evaluated unless ruled out by rigorous algebraic lower bounds. Lightness is a bound because the chroma/hue quadratic is nonnegative. Further bounds use |RT| ≤ √3 and T ≤ 1.93 to reject impossible candidates before expensive hue-angle calculations. The quadratic is at least ¼ of either squared normalized chroma/hue term, and at least (1 − √3/2) times their sum. No metric-tree/triangle-inequality assumption is made. Repeated RGB inputs reuse exact cached results; cache eviction changes speed only. With dithering, corrected floating-point inputs are matched without rounding to bytes or caching approximations.

Error diffusion remains optional, in linear RGB; palette matching still uses the chosen perceptual metric. Statistics measure the output against original pixels, not the error-corrected input, using ΔEOK or ΔE00 as labeled. These are different scales. Dithering can smooth an area average while increasing per-pixel error. For clean pixel-art regions, leave dithering off. Source images are read through a default sRGB browser canvas; alpha is preserved separately, and matching is not background-composited.

The equations and edge cases were checked against [Sharma, Wu & Dalal's 34 supplementary cases](https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/). See also [Ottosson's OKLab derivation](https://bottosson.github.io/posts/oklab/). Run `node tests/quantizer.test.cjs` for formula, exact-search, worker/alpha/dither and palette-separation checks. The reference fixture is attributed numerical test data; no reference MATLAB implementation is bundled.

The **RGB9 retro fusion** profile fixes the complete RGB333/RGB9, RGB332, and RGB222 machine palettes. Their 832 nominal entries collapse to 688 distinct sRGB colors where the systems overlap. Its remaining 336 slots are weighted farthest-point selections in OKLab from a deduplicated union of RGB444, web-safe colors, and the X Consortium's 1994 `rgb.txt`. No unrestricted RGB color can enter this profile.

The **Retro artist wheel** profile replaces the web-safe cube in an RGB333 + RGB332 + RGB233 + RGB222 + Windows-16 construction. Those historical systems contribute 816 unique anchors. Its artist vocabulary begins with 60 supplied colors, extends their five HSV signatures across 12 interstitial hues, and pairs the resulting 120 colors with 120 darker companions (`S × 0.75`, `V × 0.55`). All 120 core colors and the 94 most perceptually useful companions are retained, contributing exactly 208 new colors and bringing the palette to 1,024.

The **Lospec 19 max-fit** profile contains only verbatim colors from 19 supplied low-spec palettes. Their 1,487 entries collapse to 1,420 unique RGB colors. Eight RGB corners are fixed, then weighted farthest-point sampling in OKLab retains the 1,016 strongest remaining colors. The 396 omitted candidates are all represented by close retained neighbors; the worst omission is about 0.0186 ΔEOK away.

The **Lospec × machine max-fit** profile makes a fresh selection from the full 1,420-color Lospec union plus complete RGB333, RGB332, and RGB222 vocabularies. The three machine formats collapse from 832 nominal entries to 688 unique colors; only 32 exactly overlap the artist union, producing 2,076 legal candidates. Eight RGB corners are fixed and weighted farthest-point sampling in OKLab selects the remaining 1,016. The result contains 680 Lospec-only colors, 328 machine-only colors, and 16 colors shared by both vocabularies.

The **Retro source union 4096** profile begins with 5,576 exact candidate colors from 29 supplied palettes, RGB333/RGB332/RGB222, fixed low-bit hardware reference palettes, common software RGB arrangements, grayscale, web-safe RGB, and the X Consortium's 1994 `rgb.txt`. Exact duplicates collapse first. Selection solves the ΔE00 < 2 conflict graph for the exact maximum-cardinality subset whose colors are all at least 2.0 CIEDE2000 apart, with the optimum proven by HiGHS, before filling the unavoidable remaining slots by greatest available CIEDE2000 separation. Provenance only breaks distance ties, with X11-only colors deliberately deweighted. The finished palette contains 3,175 colors from the ≥2 stage and 921 necessary closer additions; its minimum pairwise distance is approximately 1.226 CIEDE2000.

## Distance-first 1024 subset

The new **Retro source union · distance-first · 1024** uses only unchanged colors from the shipped 4,096-color profile. Black and white are the only locked endpoints. Eight deterministic farthest-point starts in CIEDE2000 are followed by exhaustive one-color replacements at each current closest pair, accepting only strict improvements to the minimum distance. Among the eight results, minimum separation wins first, source-pool worst error second, mean error third. No source weighting can purchase a distance compromise.

- Minimum pairwise ΔE00: **4.203349480** (zero pairs below 2).
- Median nearest-neighbor ΔE00: **4.720979747**.
- Every color in the 4,096 source pool is within **4.203001511** ΔE00 of a retained entry. This is coverage of the source pool, not a guarantee over all sRGB colors.
- Every output is a literal parent entry; no centroids or invented colors.
- This maximin heuristic is audited, but **not a proof of globally optimal separation**.

Download [the package](dist/palettes/retro-source-union-1024-package.zip) or individual [TXT](dist/palettes/retro-source-union-1024.txt), [GPL](dist/palettes/retro-source-union-1024.gpl), [KPL](dist/palettes/retro-source-union-1024.kpl), [JSON/audit](dist/palettes/retro-source-union-1024.json), and [swatches](dist/palettes/retro-source-union-1024.png). Rebuild with `python scripts/build-retro-1024.py` (NumPy and Pillow). The JSON records the parent file's SHA-256, all trial scores, closest pair, and each color's parent index.

## License

MIT
