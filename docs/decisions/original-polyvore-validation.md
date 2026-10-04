# Polyvore repositories validation report

## Historical scope and current status

The report below preserves the initial metadata and anonymous-access observations.
Its "blocked" statements describe that earlier check, not the current approved
Polyvore Outfits access. Subsequent approved access on 2026-09-21 and the five-image
disjoint-validation inspection are recorded in [verification notes](dataset-verification-notes.md)
and the [sample report](../../data/samples/polyvore_outfits/inspection_report.md).
The two Polyvore releases must remain separate; newer access does not repair the
original release's tested legacy image URLs.

The earlier "zero item IDs" overlap result used outfit-position references, not
product identity. It does not establish product-level disjointness. Phase 3 reruns
also reported 98 FITB answer-index versus blank-position differences that need
dataset-owner interpretation. See [reproduction scope and commands](../REPRODUCIBILITY.md).
The historical JSON report is preserved unchanged; neither report accepts the
team's eventual leakage checks or compatibility training data.

## Preserved initial observations

## Original Polyvore metadata (xthan/polyvore-dataset)

- Archive downloaded and extracted successfully.
- Archive size: 8,412,072 bytes.
- Extracted metadata size: 58,504,139 bytes.
- Train: 17,316 outfits / 114,806 item references.
- Validation: 1,497 outfits / 9,070 item references.
- Test: 3,076 outfits / 18,604 item references.
- Split overlap: zero set IDs and zero item IDs across train/validation/test.
- Categories: 380 used IDs; zero unmapped IDs.
- FITB: 3,076 questions; zero unresolved references.
- Compatibility: 7,076 examples (3,076 compatible, 4,000 incompatible); zero unresolved references.
- Five legacy image URLs tested: all returned HTTP 403.
- Therefore metadata integrity passes, but official image access fails.

## Polyvore Outfits (mvasil)

- Repository source code downloaded. All five Python files compile under Python 3.13.
- Training execution was not attempted because the official README states the code was tested with PyTorch 0.1.12 and the dataset files are required.
- Current official Hugging Face package is gated. Anonymous access to categories.csv, split JSON, compatibility files, and Parquet image data returned HTTP 401.
- Dataset card and file tree were accessible. The package advertises 68,306 outfits, 261,058 items, nondisjoint and disjoint splits, and about 4.3 GB total storage.
- Image and row-level validation cannot be completed until access is approved with an institutional or research email.

## Result

The original dataset passes metadata validation but lacks usable official images. The newer Polyvore Outfits package is the stronger compatibility candidate because it includes images and a disjoint split, but it is currently blocked by its approval requirement.
