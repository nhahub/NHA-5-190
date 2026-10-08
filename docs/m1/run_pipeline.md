# M1 preprocessing and data loading

Hayat's loader reads the prepared M1 manifests and applies the shared image preprocessing before M2.

## Inputs

The pipeline expects these M1 handoffs at repository-relative or configurable paths:

- Clean manifest from Ziad
- Split manifest from Omar
- Taxonomy mapping from Asmaa
- Garment manifest from Hana
- Source images referenced by the manifests

The current repository does not commit the raw datasets. Keep those files under the ignored data paths and point the loader at the local copies.

## Setup

For the loader itself, install the data and ML extras:

```bash
python -m pip install -e ".[data,ml,dev]"
```

## Image loader

The image loader is in `src/wardiq/data/datasets.py`.

```python
from wardiq.data.datasets import WardiqImageDataset, load_manifest

manifest = load_manifest("artifacts/m1/sample_image_manifest.csv")
dataset = WardiqImageDataset(manifest, split="train")
sample = dataset[0]
```

The returned sample always contains the M1→M2 fields:

- `item_id`
- `source_dataset`
- `image_path`
- `category_label`
- `available_attributes`
- `bounding_box`
- `segmentation_mask`
- `split`

Extra source and traceability fields are kept alongside those required fields.
Missing values stay `None`; they are not turned into negative labels.

## Garment loader

Hana's garment manifest is loaded separately so garment-specific columns do not get added to the image-level manifest.

```python
from wardiq.data.datasets import WardiqGarmentDataset, load_garment_manifest

garments = load_garment_manifest("artifacts/m1/garment_manifest.csv")
dataset = WardiqGarmentDataset(garments, split="validation", image_root=".")
sample = dataset[0]
```

Fashionpedia bounding boxes are read as XYWH. If a usable processed box is missing, the loader checks the source XYWH field. Segmentation remains `None` because the current upstream handoff does not contain usable polygon/mask coordinates.

## Preprocessing

`src/wardiq/data/preprocessing.py` builds the shared transform:

- RGB conversion
- resize to 224×224 with bilinear interpolation
- ImageNet mean/std normalization
- random horizontal flip only for training, with `p=0.5`
- deterministic validation/test transforms

No validation/test statistics are fitted.

## Checks

Run the repository test suite:

```bash
python -m pytest
```

Run the loader-specific checks:

```bash
python -m pytest tests/test_data_loaders.py
```

For a full local run, use the canonical manifest paths agreed by the team and verify that the referenced source images exist before iterating through the loaders.

## Current limitation

The raw inventory and canonical split manifest cover all 85,815 retained records,
but only 15 source images and prototype garment derivatives are available locally.
A full image or garment run still depends on the remaining raw images and assets.

## Reproduce the committed sample handoff

Run from the repository root after installing the extras above:

```bash
python scripts/tasks.py clean-manifest
python scripts/tasks.py splits
python scripts/apply_taxonomy.py --mapped-out artifacts/m1/taxonomy_manifest.csv
python scripts/tasks.py garments
python scripts/tasks.py colors
python scripts/tasks.py test
```

The clean manifest contains 85,815 records; the optional taxonomy export adds common
and direct common categories while preserving source columns. The vocabulary retains
its proposal status in the taxonomy configuration.

Garment preparation writes `artifacts/m1/garment_manifest.csv` with 56 rows:
13 Fashionpedia crops, 5 Polyvore product photos, 5 Fashion-MNIST previews and 33 skipped parts.
Only 23 rows have `usable_derivative=True`. Images are under `data/processed/garment_crops/`.
The committed `data/manifests/garment_manifest.csv` supplies the historical identity
bridge from garment annotations to source-image IDs. Canonical split membership now
comes from Omar's `data/manifests/split_manifest.csv`; the historical garment file
is not the generated loader input. All Polyvore outfit memberships are preserved
with their item-position suffixes removed independently.

`python scripts/tasks.py splits` checks exact inventory coverage, source metadata,
official test isolation, stratification counts and source-image/outfit leakage.
It generates `artifacts/m1/splits/evaluation_manifest.csv` containing the 10,000
canonical test assignments and a checksum-bearing `split_verification.json`.
Omar's report/config mention `data/manifests/evaluation_manifest.csv`, but that
file was not included in PR #10. The generated export has its own checksum and
does not claim to match the missing file's reported bytes. Reserve it for final
evaluation; do not use it for preprocessing fitting, tuning or model selection.
All generated files can be recreated from the committed assignments on another
machine. The verifier accepts equivalent LF/CRLF inventory representations.
Full raw images are still absent from this checkout.

The generated output records `target_split`, `image_path`, numeric source category IDs,
crop-local `processed_bbox_xywh`, original source geometry and attributes where available.
Fashion-MNIST uses the supplied 280x280 previews; `native_resolution_scale=0.1` describes
their relationship to the unavailable native 28x28 images, not a resize performed by this script.
Polyvore filename recovery requires a unique suffix match and is recorded in `path_resolution`.
Polyvore leakage groups use all outfit IDs without item-position suffixes.

Built-in garment transforms flip pixels and boxes together once, then resize using
`image_size: [height, width]`. Custom transforms must preserve geometry; arbitrary spatial
transforms supplied by callers require their own matching annotation handling.
For callers outside the repository, supply an absolute `image_root` when loading relative paths.

The garment command also generates `artifacts/m1/sample_image_manifest.csv`, containing
all 15 delivered source images with original traceability, aligned source labels,
proposed common categories and canonical target splits. This is the runnable prototype
input for `WardiqImageDataset`; full-image runs still require usable paths and
decoded images for the larger inventory.

```python
from wardiq.data.datasets import WardiqImageDataset, load_manifest

images = load_manifest("artifacts/m1/sample_image_manifest.csv")
dataset = WardiqImageDataset(images, split="validation", image_root=".")
sample = dataset[0]  # RGB tensor, shape [3, 224, 224]
```
