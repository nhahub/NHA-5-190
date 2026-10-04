# WARDIQ Milestone 1 — Repository Dataset Handoff

The shared repository contains the image-level raw manifest, directory convention,
dataset-to-task decisions, verified samples, evidence reports, and reproducibility
scripts. Large raw datasets remain local. Eyad's research foundation is ready for
review; the complete M1 preprocessing, splitting, cropping, taxonomy, and loader
handoff remains pending the assigned owners' work and downstream review.

## Current dataset decisions

- **Fashionpedia:** provisionally selected for garment detection, segmentation, categories, and attributes until training annotations are verified.
- **Polyvore Outfits:** selected for outfit compatibility and recommendation; use the disjoint split for evaluation.
- **Fashion-MNIST:** use only for basic loading, preprocessing, and classification pipeline checks.
- **DeepFashion-MultiModal:** backup only.

## Start today

1. Work from the existing repository clone and create your task branch from `main`.
2. Review [data conventions](../../data/README.md), [dataset mapping](../decisions/dataset-selection.md), and [verification notes](../decisions/dataset-verification-notes.md).
3. Ziad and Asmaa should review `data/manifests/raw_manifest.csv` and confirm that IDs and file references are understandable. Asmaa's canonical full name still needs owner confirmation; this does not change her assignment.
4. The team may develop loaders and preprocessing code against the included samples.
5. Preserve all original source IDs and split names in generated outputs.
6. Keep large raw datasets local. Do not redistribute source images outside the project team.

## Repository checks and raw inputs

Run from the repository root with normal Python:

```powershell
python -m pip install -e ".[dev,data]"
python scripts/tasks.py validate
python scripts/tasks.py samples
python scripts/tasks.py links
```

These checks validate repository infrastructure and the 15 committed sample images;
they do not accept the team's full preprocessing pipeline or establish split leakage
freedom. Follow [research reproduction](../REPRODUCIBILITY.md) for raw inputs,
canonical paths, CLI overrides, and manifest comparison. Record the Git revision
when sharing progress in Notion instead of copying another temporary ZIP.

The raw manifest currently covers 70,000 Fashion-MNIST images, 1,158 Fashionpedia
validation images, and 14,657 Polyvore disjoint-validation items. It is an inventory,
not a model-ready training dataset. Fashionpedia training verification, team pipeline
outputs, and cross-split product-level leakage checks remain pending. The source
samples include enlarged Fashion-MNIST previews; actual loading uses native IDX.

Use the [M1 completion checks](M1.md) and [handoff review packet](../HANDOFFS.md)
for downstream acceptance. Code licensing, rights to redistribute existing sample
images, and reviewer identities remain owner decisions.

## Official sources

- Fashionpedia: https://github.com/cvdfoundation/fashionpedia
- Polyvore Outfits: https://huggingface.co/datasets/mvasil/polyvore-outfits
- Fashion-MNIST: https://github.com/zalandoresearch/fashion-mnist
- DeepFashion-MultiModal: https://github.com/yumingj/DeepFashion-MultiModal
