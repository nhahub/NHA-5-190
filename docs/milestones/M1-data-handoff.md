# WARDIQ Milestone 1 — Temporary Dataset Handoff

This package lets the team begin before the instructor provides the repository. It contains an image-level raw manifest, the agreed directory convention, dataset-to-task decisions, verified samples, evidence reports, and reproducibility scripts. It does not contain the large raw datasets.

## Current dataset decisions

- **Fashionpedia:** provisionally selected for garment detection, segmentation, categories, and attributes until training annotations are verified.
- **Polyvore Outfits:** selected for outfit compatibility and recommendation; use the disjoint split for evaluation.
- **Fashion-MNIST:** use only for basic loading, preprocessing, and classification pipeline checks.
- **DeepFashion-MultiModal:** backup only.

## Start today

1. Extract this ZIP without renaming files.
2. Review `data/README.md`, `docs/dataset_mapping.md`, and `docs/review_corrections.md`.
3. Ziad Nasser and asmaa farahat should load `data/manifests/raw_manifest.csv` and confirm that IDs and file references are understandable.
4. The team may develop loaders and preprocessing code against the included samples.
5. Preserve all original source IDs and split names in generated outputs.
6. Keep large raw datasets local. Do not redistribute source images outside the project team.

## Temporary folder convention

See `data/README.md` for the complete convention and traceability rules.

When the official repository arrives, copy these folders into it, record the final paths in Notion, and ask Ziad and asmaa to repeat the manifest check.

## Official sources

- Fashionpedia: https://github.com/cvdfoundation/fashionpedia
- Polyvore Outfits: https://huggingface.co/datasets/mvasil/polyvore-outfits
- Fashion-MNIST: https://github.com/zalandoresearch/fashion-mnist
- DeepFashion-MultiModal: https://github.com/yumingj/DeepFashion-MultiModal
