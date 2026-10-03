# WARDIQ data convention — Milestone 1

This temporary structure is ready to copy into the instructor's repository. Raw data remains unchanged, derived files go under `processed/`, and every usable image has one row in `manifests/raw_manifest.csv`.

## Directory convention

```text
data/
├── raw/
│   ├── fashion_mnist/
│   ├── fashionpedia/
│   └── polyvore_outfits/
├── processed/
│   └── <dataset>/<pipeline-version>/
├── samples/
│   ├── fashion_mnist/
│   ├── fashionpedia/
│   └── polyvore_outfits/
└── manifests/
    └── raw_manifest.csv
```

## Manifest rule

The row unit is **one row per image**. Object annotations remain linked through `annotation_ids` and `annotation_reference`; this avoids duplicating image rows when an image has several garments or garment parts.

- Fashion-MNIST has no filenames or external source IDs. Its stable ID is generated as `fashion_mnist_<split>_<zero-padded-index>` and the split/index must be preserved.
- Fashionpedia keeps the official image ID and filename. All category, attribute and annotation IDs for the image are semicolon-separated in the same row.
- Polyvore Outfits keeps the official item ID. Outfit membership is stored as `<set_id>:<item_index>` in `outfit_ids`.
- Do not map categories across datasets in Milestone 1; their taxonomies are not interchangeable.

## Releases and access

| Dataset | Files used | Access and registration | Current local scope |
|---|---|---|---|
| Fashion-MNIST | Four official IDX gzip files: train/test images and labels | Direct download or `torchvision.datasets.FashionMNIST`; no account required. [Official repository](https://github.com/zalandoresearch/fashion-mnist) | 60,000 train + 10,000 test images |
| Fashionpedia | `val_test2020.zip` and `instances_attributes_val2020.json` | Direct official download; terms apply. [Repository](https://github.com/cvdfoundation/fashionpedia) · [Terms](https://fashionpedia.github.io/home/data_license.html) | 1,158 validation images; 8,781 linked annotations |
| Polyvore Outfits | Hugging Face `data/disjoint/validation-00000-of-00001.parquet`, plus `metadata.json` and `disjoint/valid.json` | Gated research access; access was approved and downloaded on 2026-09-21. [Dataset page](https://huggingface.co/datasets/mvasil/polyvore-outfits) | 14,657 disjoint-validation item images |

## Team workflow

1. Copy this `data/` folder and `scripts/` into the official repository when it arrives.
2. Put downloaded source files in the paths listed in `original_image_reference` and `annotation_reference`.
3. Keep `data/raw/` read-only during processing.
4. Write outputs to `data/processed/<dataset>/<pipeline-version>/` and keep `item_id` in every derived record.
5. Run the sample checks in `data/samples/` before a loader is accepted.

## Current limitations

- Fashionpedia is provisionally selected until its training annotations are downloaded and verified. The public repository exposes train and validation annotations plus test image information; it does not expose labeled test annotations. [Official downloads](https://github.com/cvdfoundation/fashionpedia#download)
- DeepFashion-MultiModal is documented as a backup, but no local sample has been checked. [Official repository](https://github.com/yumingj/DeepFashion-MultiModal)
- The manifest records only data currently available to the team. Regenerate it after new official files are added.
