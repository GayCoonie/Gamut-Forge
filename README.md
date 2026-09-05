# Gamut Forge

A static, client-side image quantizer for arbitrary fixed palettes—including palettes larger than 256 colors.

## What it does

- Two selectable exact matching engines: fast OKLab k-d tree and CIEDE2000
- Optional serpentine Floyd–Steinberg dithering in linear-light RGB
- Imports GIMP `.gpl`, hex text, JSON containing hex colors, and flat-color palette images
- Includes twenty-six 1024-color palettes and four 4096-color palettes, including game-derived Static Bloom material ramps, a complete RGB343 control, three HSV three-tier experiments, and the retro source unions
- Preserves transparency and exports an RGBA PNG
- Reports used colors, mean and maximum error in the chosen metric, processing time, and palette conformance
- Cancelable processing, downloadable TXT/GPL/KPL/JSON palettes, and an interactive lightness/chroma atlas

Everything runs in the browser. No image or palette is uploaded.

## Palette library

The home page links to [the complete palette library](dist/palette-library.html). All 30 built-ins have descriptions, a shared CIELAB atlas, direct quantizer links and TXT/GPL/KPL/JSON/PNG/ZIP downloads. The three HSV variants also link to their construction diagrams. Existing audited exports are preserved; missing legacy exports are copied from the exact shipped color arrays, without resampling or reordering. Rebuild the catalog with `python scripts/build-palette-library.py` (Node and Pillow required).

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

## Static Bloom: game-derived material palettes

The **Static Bloom 1024** and **Static Bloom 4096** profiles are designed for palette crushing Coonie Critters' varied terrain, creatures, fabric, wood, stone and bright technology. They use new colors derived from a compact material design, not a subset of the historical pool. The 1024 profile is nested verbatim inside the 4096 profile. Neither profile relaxes the minimum 2 ΔE00 requirement.

| Profile | Colors | Minimum pairwise ΔE00 | Median nearest-neighbor ΔE00 |
| --- | ---: | ---: | ---: |
| Static Bloom 1024 | 1024 | 4.565380239 | 5.062758382 |
| Static Bloom 4096 | 4096 | 2.787773732 | 3.111116405 |
| RGB343 control | 1024 | 0.367331153 | 2.534393949 |

The design learns from **42 of the game's 52 runtime atlases**, holding back ten complete atlases, including the snow/ground bank, interior-material bank and one Critter atlas. It samples foreground pixels with alpha ≥192, balances six asset categories equally, and then balances atlases within each category. This prevents large terrain sheets from overwhelming characters, creatures or items. Source images remain private; the repository contains only an aggregate design manifest, the generated colors and evaluation statistics.

Nineteen shared OKLab lightness steps blend 65% regular spacing with 35% category-balanced source-lightness quantiles. The design has 64 learned hue/chroma material families alongside 48 general hue directions. Ramps bend gently toward indigo in shadows and gold in highlights. Chroma falls toward the lightness endpoints; out-of-gamut candidates reduce chroma at fixed lightness and hue before 8-bit rounding. A single neutral spine supplies true grays. This applies the artistic idea of connected, hue-shifting ramps described by [Raymond Schlitter](https://www.slynyrd.com/blog/2018/1/10/pixelblog-1-color-palettes), with [OKLab](https://bottosson.github.io/posts/oklab/) controlling the ramp geometry instead of HSV.

After exact RGB deduplication, pure CIEDE2000 farthest-point selection chooses 1024 colors from 8625 coarse candidates, starting with black and white. The 4096 extension starts with those 1024 colors and adds 3072 from a 53,252-color refined candidate pool: 55 lightness steps, 96 general hue directions and additional chroma levels. Asset weights shape the candidate vocabulary; they **never multiply the selection distances** or override separation. The stated minima are exhaustive pairwise measurements, independently cross-checked by the JavaScript implementation. This is a deterministic design/maximin heuristic, not a proof of the globally best palette or an image-specific error optimum.

The same ten held-out atlases supply 5120 evaluation pixels, mapped by exact CIEDE2000 without dithering:

| Profile | Mean ΔE00 | 95th-percentile ΔE00 | Maximum ΔE00 |
| --- | ---: | ---: | ---: |
| Static Bloom 1024 | 2.692 | 4.108 | 6.090 |
| Previous retro 1024 | 2.722 | 4.316 | 7.117 |
| Static Bloom 4096 | 1.696 | 2.570 | 4.585 |
| Previous retro 4096 | 1.861 | 3.536 | 6.908 |
| RGB343 control | 3.487 | 6.464 | 9.344 |

These are sample fidelity measurements, not a pixel-art aesthetic score or a guarantee for every game image. The palette supplies shared steps and distinct alternatives; nearest-color mapping still cannot enforce spatial clusters or remove detail by itself. The 1024 profile favors stronger simplification; 4096 supplies more material distinctions. Both matching engines remain available, with no dithering recommended for the cleanest regions.

Explore the [single-page atlas](dist/palette-guide.html), or download [Static Bloom 1024](dist/palettes/static-bloom-1024-package.zip), [Static Bloom 4096](dist/palettes/static-bloom-4096-package.zip), and [RGB343](dist/palettes/rgb343-control-package.zip). Each ZIP contains TXT, GIMP GPL, Krita KPL, JSON audit and an exact swatch PNG. The atlas places actual colors on twelve CIELAB lightness/chroma hue pages and also offers a view of every swatch.

**RGB343** means 3 bits of red, 4 bits of green, and 3 bits of blue: **8×16×8 = 1024** colors. Its red/blue levels are `[0,36,73,109,146,182,219,255]`; green uses multiples of 17. This is rounded full-range code expansion, not a simulation of any particular display's analog DAC. All cube entries are retained for the control, so perceptual pruning does not apply; it has 342 pairs below 2 ΔE00.

Rebuild from the committed aggregate manifest with `python3 scripts/build-critter-palettes.py` (NumPy, Pillow). To relearn the manifest from the owner's v11.1.0 archive, add `--source-zip PATH`. `scripts/evaluate-critter-palettes.py --source-zip PATH --review-dir PRIVATE_DIRECTORY` writes the aggregate evaluation and private visual comparisons. Run `node tests/critter-palettes.test.cjs` to verify every pair, nesting, full cube membership and export equality; run the existing quantizer suite to check both engines.

## HSV three-tier redesign and 10% grid comparison

Both new profiles have **64 hues at 5.625° spacing**. The 64/32/16 subsets are nested: indices 0–63, every second index, and every fourth index. Each active tier contributes nine colors, giving **576 + 288 + 144 = 1008 chromatic colors**, followed by **16 true grays**, evenly spaced in HSV value (RGB 0,17,…,255). Both contain exactly 1024 unique RGB triplets; no duplicate removal or filler colors are needed.

The primary **HSV three-tier 64/32/16** follows the requested bounds: the core is the Cartesian 3×3 product of S,V = 2/3, 5/6, 1. Each added band has **three nested three-point Ls**. For a previous boundary b and new boundary a, levels are q = b + (a−b)k/3 for k=1,2,3; each L contains (S,V) = (q,1), (q,q), (1,q). The middle band's levels are 5/9, 4/9, 1/3; the outer band's are approximately 26.8889%, 20.4444%, 14%. This includes both ends and the bend of every L, with equal level spacing and no repeated previous boundary. The two added areas are disjoint from their preceding squares. The exact coordinates are supplied for inspection.

The **10% grid comparison** retains those hue/sample counts and the gray ramp, but every chromatic S and V coordinate belongs to {0.1,0.2,…,1}. Its core is the exact 80/90/100% Cartesian grid. The remaining seven levels are split between a middle band with min(S,V) = 40–70%, and an outer band with min(S,V) = 10–30%. Each band retains three extreme corners and chooses six more points by deterministic Euclidean farthest-point initialization and uniform-lattice medoid refinement. The 80/40/10% bounds are an explicit implementation choice to retain a three-level core and use all ten allowed levels across the available domains. The grayscale is still 16 levels, not restricted to the ten-percent lattice.

All placement uses **HSV geometry**, with conventional HSV→sRGB code conversion and nearest-integer rounding (half up, resolving floating-point ties). Neither version applies perceptual weighting, pruning or a ΔE floor. Their audited minimum ΔE00 values are approximately **0.295** and **0.219**, respectively; dense fully saturated hue regions naturally include very close perceptual neighbors. These are structural HSV experiments alongside the distance-first profiles.

Open the [sample diagrams and downloads](dist/hsv-three-tier.html), or get the [thirds/14% package](dist/palettes/hsv-three-tier-64-package.zip) and [10% grid package](dist/palettes/hsv-three-tier-10-package.zip). Each includes TXT, GPL, KPL, JSON audit, exact HSV coordinates and a swatch PNG. The interactive diagrams show the true square/L boundaries, numbered points and hue-subset membership on identical S/V axes.

Rebuild both with `python3 scripts/build-hsv-three-tier.py` (NumPy, Pillow); verify them independently with `node tests/hsv-three-tier.test.cjs`.

## HSV sketch spread

The additional **HSV three-tier · sketch spread** profile translates the owner's colored-dot sketch into a precise layout. It keeps the green 3×3 core, uses **2/2/5 purple points** across three rows in the middle band, and **3/2/4 yellow points** across three rows in the outer band. Counts, hue subsets, bounds and grays stay at 64/32/16 hues, nine samples per tier, 14% outer limit, and 16 HSV-linear grays: **1024 unique colors**.

Exact S/V placement (coordinates below are fractions of full scale):

| Band / row | Value | Saturation positions |
| --- | ---: | --- |
| Core: each of three rows | 1, 5/6, 2/3 | 2/3, 5/6, 1 |
| Middle: top | 1 | 1/3, 1/2 |
| Middle: center | 2/3 | 1/3, 1/2 |
| Middle: bottom | 1/3 | 1/3, 1/2, 2/3, 5/6, 1 |
| Outer: top | 1 | 0.14, 0.204444…, 0.268889… |
| Outer: center | 1/2 | 0.14, 0.268889… |
| Outer: bottom | 0.14 | 0.14, 1/3, 2/3, 1 |

These coordinates are an explicit interpretation of the sketch's row structure, not digitized hand-drawn dot positions. The outer top's three S coordinates divide the 14%-to-1/3 band into thirds while excluding the already-sampled 1/3 boundary. There is no perceptual fitting, pruning or invented filler. The earlier profiles' color files remain unchanged.

For hue indices with all three tiers, the mean nearest-sample Euclidean S/V gap on a 400×400 uniform midpoint grid over [0.14,1]² falls from 0.12414 to 0.08725; the largest sampled gap falls from 0.36013 to 0.22190. This measures **HSV-plane coverage**, not perceptual color error or image quality. Minimum pairwise ΔE00 remains approximately 0.295 because the dense 64-hue core is unchanged.

The [interactive sampling page](dist/hsv-three-tier.html?version=sketch) now includes a combined green/purple/yellow overview like the sketch, plus individual band diagrams and exact coordinates. [Download the package](dist/palettes/hsv-three-tier-sketch-package.zip) for TXT, GPL, KPL, JSON audit, geometry and swatches. Rebuild this profile with `python3 scripts/build-hsv-sketch.py`; the shared `node tests/hsv-three-tier.test.cjs` verifies all three profiles.

## License

MIT

## Random Strata Beta

Four user-supplied Gemini-assisted trials retain their exact 1,024 RGB colors and original order. Their minima are 0.238, 0.306, 0.270 and 0.300 ΔE00: the requested global 2.5 rule was not met. The combined beta preserves all 3,777 unique colored entries, includes all 256 grays, and adds 63 deterministic farthest-point samples (minimum added separation 4.669 ΔE00). The raw deduplicated source union is 3,949 colors. The combined profile is deliberately not globally separated. See [the beta report and corrected generator](dist/random-strata.html).

`python scripts/build-random-strata.py /path/to/gpl/files` rebuilds from try1.gpl through try4.gpl; original source hashes are recorded without publishing local source paths. `python scripts/build-palette-library.py` refreshes the catalog. The standalone `scripts/generate-random-strata.py` (v2) uses only the standard library. It samples 64 near-grays from the 15,436 RGB colors with max(channel) - min(channel) <= 4, forcing black and white, and excludes that pool from all hue blocks. Each vivid row gets an adaptive target from an exact eight-clique feasibility search over all byte RGB vivid candidates, capped at the global target and otherwise given a 0.2 margin (at most half the capacity). Capacities are conditional on previously selected vivid rows, not globally optimal joint allocations. Cross-sector vivid pairs use the smaller target; other pairs retain the global 2.5 default. Fresh random seeds are recorded unless `--seed` is given. Retries are finite and a final all-pairs audit checks all configured constraints. The seed-42 example succeeds with 64 near-grays at least 2.5045 apart, every other non-vivid pair class above 2.5, and zero configured violations. Source and download copies are identical. Run `python tests/random-strata.test.py` for reference, exact-search, geometry, anchor and reproducibility checks.

## Random Strata v2: Try 5–8

Four user-supplied 1,024-color runs are preserved exactly, including Try 8’s different exported ordering. All contain 64 near-grays, 120 vivid entries and 840 quadrant samples. Independent audits find every non-vivid–vivid pair at least 2.5 ΔE00 apart. Seeds and per-sector configured targets were not supplied.

The combined 4,096 palette retains their 4,001-color exact union, replaces six duplicate black/white occurrences with missing full-range RGB3 gray levels (36, 73, 109, 146, 182, 219), and fills 89 other duplicates using only Try 1–4 colors, chosen by deterministic CIEDE2000 farthest-point selection. Minimum borrowed-color separation is 3.698572 ΔE00. Existing close cross-trial pairs remain: the combined global minimum is 0.007470. The JSON replacement ledger preserves all provenance. Rebuild with `python scripts/build-random-strata-v2-trials.py /path/to/uploads`, then refresh the palette library.
