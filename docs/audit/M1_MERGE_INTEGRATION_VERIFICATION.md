# M1 merged-code integration verification

> This records the earlier PR #8 review. For the checkout after merging Omar's
> canonical splits and Eyad's M2 color component, see
> [the updated M1/M2 pull verification](M1_M2_PULL_VERIFICATION.md).

Date: 2026-10-08. Reviewed checkout: `main` at `84b97fe`, including Asmaa's
taxonomy PR #7, Hana's garment PR #6 and Hayat's loader fixes PR #5.
The fixes described here are local working-tree changes.

## Defects corrected

- Garment generation did not produce `target_split`, `usable_derivative` or
  `image_path`, so its output could not be consumed by the garment loader.
  The new generated manifest includes these columns and preserves the delivered
  sample split membership from the committed historical garment CSV.
- Invalid or missing bbox strings raised before fallback. Malformed, nonfinite,
  zero/negative and fully outside boxes now retain a flagged full image.
  Fractional valid boxes enclose actual pixels using floor/ceil boundaries.
- Crop metadata used source-image coordinates for processed images. Crop-local
  boxes now use the saved crop dimensions; original and clamped source boxes
  remain separate.
- Polyvore and Fashion-MNIST rows used inconsistent dataset names and text in
  numeric category fields. Generated rows now use canonical source names and IDs.
  Polyvore item identities join to the delivered image-level key; leakage groups
  use the outfit ID without its position suffix.
- Image filename recovery silently selected the first suffix match. Recovery
  now requires a unique match and records how the image path was resolved.
  Source paths reference the actual delivered files.
- Fashion-MNIST's reported resize scale suggested a resize that never happened.
  Preview provenance and native-resolution scale are now separate fields.
- Garment training flipped pixels manually and again inside torchvision, while
  transforming boxes once. Flipping is now performed once jointly with boxes.
  Torchvision's `[height, width]` ordering is respected for non-square images.
- String boolean values and invalid boxes were parsed incorrectly. Boolean
  parsing is explicit and box parsing rejects nonfinite/nonpositive geometry.
  Available garment attribute IDs are retained.
- Taxonomy CLI defaults referenced an absent clean manifest. They now point at
  the reproducible quality output. Unknown IDs are reported without a lookup
  crash, and an optional mapped export preserves original source columns.
- Generated data is kept in ignored output directories. The committed source
  manifests remain unchanged. Both merged scripts are now in lint/format checks,
  pre-commit routing and CI execution.

## Reproduction

Install the declared environment and run from the repository root:

```bash
python -m pip install -e ".[data,ml,dev]"
python scripts/tasks.py clean-manifest
python scripts/apply_taxonomy.py --mapped-out artifacts/m1/taxonomy_manifest.csv
python scripts/tasks.py garments
python scripts/tasks.py lint
python scripts/tasks.py format-check
python scripts/tasks.py typecheck
python scripts/tasks.py test
python scripts/tasks.py validate
python scripts/tasks.py links
python scripts/tasks.py duplicates
python scripts/tasks.py m1-images
python scripts/tasks.py samples
```

The local review used the existing pandas/PyYAML environment and an ignored
`.local-check-tools` directory for downloaded test tools and PyTorch/torchvision.
Tests ran on Python 3.13. Other Python versions remain covered by the CI matrix;
remote CI has not run against these uncommitted changes.

## Verified results

- 46 tests passed, plus 6 subtests. Regression coverage executes crop generation
  from another working directory, malformed-box fallbacks, unknown taxonomy IDs,
  string booleans, non-square resizing and an actual asymmetric training flip.
- All 15 delivered source images and 23 generated garment derivatives load through
  real PyTorch/torchvision transforms into finite RGB tensors of shape `[3,224,224]`.
- 56 garment rows: 13 Fashionpedia crops, 5 Polyvore images, 5 Fashion-MNIST
  previews and 33 excluded parts. Split membership is unchanged; usable counts
  are 5 training and 18 validation derivatives.
- The prototype image manifest contains 15 source images: 5 training and 10 validation.
- The clean manifest has 85,815 unique records. Source-ID lookup corrects 1,095
  Fashionpedia label-order rows. Every observed category ID has taxonomy coverage;
  the cleaned Fashionpedia label sets match the ID lookup.
- Lint, formatting, package type checks, repository/artifact validation, local
  documentation links, source image decoding and reference-duplication checks pass.

## Limits of verification

The full raw images and canonical complete split/integrated manifests are not in
this checkout. Full-scale image loading, model training and test-set leakage
acceptance cannot be established from this prototype. Historical reports describing
those external artifacts remain historical evidence.

Fashion-MNIST inputs are upscaled grayscale previews, not native files or useful
color-extraction data. Masks remain unavailable: segmentation flags do not contain
mask coordinates. The common taxonomy retains its proposal status; original source
labels remain authoritative. Existing visual concerns about the jacket/watch crops
are not resolved merely by successful decoding.

Custom image transforms supplied by callers must preserve geometry or provide their
own paired annotation handling; automatic geometry synchronization covers the built-in
transforms. Nothing has been committed, pushed or merged by this review.
