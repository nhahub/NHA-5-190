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

manifest = load_manifest("data/manifests/integrated_m1_manifest.csv")
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

garments = load_garment_manifest("data/manifests/garment_manifest.csv")
dataset = WardiqGarmentDataset(garments, split="validation")
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

The image-level M1 manifest covers all 85,815 retained records, but the current upstream handoff only includes prototype garment derivatives. A full garment run still depends on the remaining raw images and garment assets being available.
