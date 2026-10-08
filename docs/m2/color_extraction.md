# Eyad's M2 color extraction

The reusable component extracts dominant palettes from ordinary RGB garment images
without waiting for model selection or Omar's split push. Final Polyvore cache assembly
is a separate phase requiring Hanaa's frozen contract and the selected model components.

Task requirements: [garment-aware LAB extraction](https://app.notion.com/p/3e998a0a49c08116b3a0e50633e08980).
Palette interface: [Hanaa's initial item output](https://app.notion.com/p/3ea98a0a49c0818ea81de73677cf2305).

## Run the sample pipeline

From the repository root:

```powershell
python -m pip install -e ".[data,color,dev]"
python scripts/tasks.py garments
python scripts/tasks.py colors
```

To run the entire repository suite, also install the `ml` extra, which the M1 loader
tests require. `python scripts/tasks.py setup` installs all required extras.

The color CLI accepts explicit paths and works from other directories:

```powershell
python scripts/extract_color_palettes.py --manifest artifacts/m1/garment_manifest.csv --config configs/m2/color_extraction.yaml --output-dir artifacts/m2/color/v1 --image-root .
```

The generated outputs are ignored by Git:

| File | Purpose |
|---|---|
| `artifacts/m2/color/v1/palettes.jsonl` | One success, failure or exclusion record per input row |
| `artifacts/m2/color/v1/coverage.json` | Reconcilable counts, versions and input/config/implementation checksums |
| `artifacts/m2/color/v1/palette_contact_sheet.png` | Source images and palette swatches for review (at most 24 by default) |

On the supplied manifest: 56 rows = 18 successes + 38 exclusions + 0 failures.
Successes are 13 Fashionpedia crops and 5 Polyvore photos. Exclusions are 33 garment
parts without derivatives and 5 grayscale Fashion-MNIST smoke-test previews.
This does not establish full-dataset coverage.

## Reuse the extractor

```python
import numpy as np
from PIL import Image
from wardiq.clothing.color_extraction import ColorConfig, extract_palette

with Image.open("garment.png") as image:
    pixels = np.asarray(image.convert("RGBA"), dtype=np.uint8)

result = extract_palette(pixels, ColorConfig(k=5, seed=42), region_method="bbox_crop")
# region_method="bbox_crop" means this file is an already-prepared crop.
# Optional mask=HxW array or bbox_xywh=[x,y,w,h] must match these image coordinates.
if result["status"] == "ok":
    palette = result["palette"]
```

Direct callers supply sRGB pixels. The file runner honors embedded ICC profiles by
converting them to sRGB; untagged images are assumed to be sRGB. EXIF orientation is
not changed because the prepared crops already define their pixel coordinate frame.
Images are not resized, model-normalized or white-balanced during extraction.

## Region and fallback policy

Valid mask pixels are preferred, then a supplied valid bounding box, then the full
image if policy allows it. Positive mask values are foreground. Masks must be finite,
nonempty and match image dimensions. Transparent pixels are excluded using the
configured alpha threshold. Fractional boxes enclose pixels using floor/ceil and
are clamped to image bounds.

The CLI reads already prepared images: `bbox_crop` indicates a derivative crop;
`full_image_source_precropped` indicates a source product photo. Optional `mask_path`
is interpreted in the prepared image's coordinates. A segmentation-present flag
alone is not a usable mask. Missing/invalid masks are recorded as fallback warnings.

Every unmasked result has `background_contamination_possible=true`, including boxes
and product photos. Full-image fallback is explicitly flagged. White pixels are not
automatically removed: that could remove a white garment. No inferred segmentation
or fabricated isolation is applied. Missing images fail with a reason and a nonzero
CLI exit status; they are never silently excluded as successful inputs.

## LAB and clustering conventions

LAB is physical CIE L*a*b* using the sRGB D65 reference white and 2-degree observer.
It is not OpenCV's packed 8-bit LAB and not CSS's D50-adapted LAB. The implementation
linearizes sRGB, converts to XYZ D65, normalizes by that reference white and applies
the CIE LAB piecewise function. See the
[W3C conversion formulas](https://www.w3.org/TR/css-color-4/#color-conversion-code).
The inverse conversion is used only to display swatches, clipping display RGB gamut.

Hanaa's initial palette field ranges are enforced: L `[0,100]`, a/b `[-128,127]`,
finite numbers and nonnegative proportions. Successful sums use tolerance `1e-6`,
stricter than the interface's `0.01`. The D65 convention is included in provenance
and must be retained or explicitly reconciled during final integration.

`configs/m2/color_extraction.yaml` specifies K, seed, maximum fit pixels, restarts,
iterations, prediction batch size, alpha threshold and fallback policy. Defaults:
K=5, seed=42, at most 20,000 fit pixels, 10 restarts, 300 iterations, Lloyd algorithm.
See [scikit-learn KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html).

Uniform sampling is deterministic. Duplicate sample colors are fit with population
weights; K is reduced to the available distinct colors for solid/tiny regions.
All usable region pixels are assigned to the fitted centers in batches, so exported
proportions describe the whole selected region, not just the fit sample. Colors are
sorted by descending population with a LAB tie-break. Numerical thread pools are
limited to one thread. The CLI defaults the joblib CPU budget to one, avoiding
physical-core probing on Windows machines without WMIC. Reproducibility is checked in the same dependency environment;
library versions are recorded rather than assuming equality across all versions.

## Output and handoff

`palettes.jsonl` is a color-component artifact, not a fabricated complete item
representation. Successful records expose `color.palette` with `L`, `a`, `b` and
`proportion`; other model outputs are not invented. Each record retains stable
item/source IDs, image path, split/group metadata, region/fallback method, pixel
counts, image hash, config hash and extractor version. The report also records
source commit and implementation hash, so uncommitted implementation edits remain
traceable. Every run recomputes outputs; stale palette reuse is not performed.

Read [the reviewed sample findings](color_sample_review.md) before using palettes
as final garment-only features. Supply the component, configuration, sample outputs
and review findings to Hanaa. In Notion, attach the PR and reproduction instructions,
move the color task to In Review, and mark it Completed only after team review.
No Notion task state is changed automatically by this implementation.

Tests cover reference colors, solid/two-color proportions, mask priority, alpha,
invalid and tiny regions, deterministic sampling, full input accounting, missing
image failure and repeatable CLI exports:

```powershell
python -m pytest tests/test_color_extraction.py
python scripts/tasks.py test
python scripts/tasks.py lint
python scripts/tasks.py typecheck
```

## Later cache phase

Prepare cache I/O early, but release the cache only against Hanaa's frozen contract
and selected category/attribute/embedding components. Include your palettes and all
component versions; account for unavailable images and failures, support resume
without duplicate keys, validate vector dimensions/norms and run an M3 loading check.
See [the separate cache task](https://app.notion.com/p/3e098a0a49c081f39b97eaf3039affa0).
