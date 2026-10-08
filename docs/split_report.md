# M1 Split Report

## 1. Overview

This report documents the reproducible train/validation/test split process for the WARDIQ M1 data foundation.

The raw input manifest was used without modification. Split assignments were generated deterministically where a new split was required, while official source splits were preserved where available.

## 2. Input Manifest

- File: `data/manifests/raw_manifest.csv`
- Rows: 85815
- Columns: 17
- SHA-256: `6fc8e4e2b1f6a2f02c9582b3d9b208cb9240a0cdae7fc3d729e22be196c8aae1`

The raw manifest was not modified during split generation.

## 3. Source Releases

| Dataset | Source Release |
|---|---|
| Fashion-MNIST | zalando-research/fashion-mnist IDX release |
| Fashionpedia | Fashionpedia 2020 |
| Polyvore Outfits | mvasil/polyvore-outfits Hugging Face parquet repack |

## 4. Final Split Summary

| Dataset | Train | Validation | Test |
|---|---:|---:|---:|
| Fashion-MNIST | 54,000 | 6,000 | 10,000 |
| Fashionpedia | 0 | 1,158 | 0 |
| Polyvore Outfits | 0 | 14,657 | 0 |
| **Total** | **54,000** | **21,815** | **10,000** |

## 5. Fashion-MNIST

The official Fashion-MNIST test split was preserved and isolated.

The official training split was divided into:
- 90% training
- 10% validation

The split used:
- Random seed: `42`
- Stratification field: `category_labels`
- Method: stratified random split

All 10 Fashion-MNIST categories are represented in every split.

Each category has:
- 5,400 training records
- 600 validation records
- 1,000 test records

No category has zero coverage in any split.

## 6. Fashionpedia

The available Fashionpedia records in the current raw manifest belong to the official validation split.

The official validation split was preserved without creating a new random allocation.

The current handoff contains only 1,158 validation records. No missing training or test records were inferred or fabricated.

Source-image grouping was checked to ensure that an image does not appear in multiple target splits.

Public test labels are not available, so the test split must not be used for model selection.

## 7. Polyvore Outfits

The available Polyvore records in the current raw manifest belong to the official `disjoint validation` split.

The official split was preserved without randomly splitting individual parquet rows.

Outfit-level grouping was checked using the available `outfit_ids` information.

The current handoff contains 14,657 validation records. No missing training or test records were inferred or fabricated.

Checks found no Polyvore item ID or outfit ID appearing in multiple target splits.

## 8. DeepFashion-MultiModal

DeepFashion-MultiModal was treated as backup-only.

No split generation or download was performed for this dataset.

## 9. Assignment Completeness

Every raw-manifest item received exactly one target split.

- Raw manifest unique items: **85815**
- Split manifest unique items: **85815**
- Items with exactly one assignment: **85815**
- Items with multiple assignments: **0**
- Items missing from the raw manifest: **0**
- Extra items in the split manifest: **0**

Status: **PASS**

## 10. Count Reconciliation

The number of records in the split manifest exactly matches the raw manifest for every dataset.

- Fashion-MNIST: 70,000 → 70,000
- Fashionpedia: 1,158 → 1,158
- Polyvore Outfits: 14,657 → 14,657

Total:
- Raw manifest: **85,815**
- Split manifest: **85,815**

Status: **PASS**

## 11. Leakage Checks

The following checks were performed:

| Check | Result |
|---|---|
| Duplicate item IDs | 0 |
| Item IDs across multiple target splits | 0 |
| Source-image identities across multiple target splits | 0 |
| Fashion-MNIST official test overlap | 0 |
| Fashionpedia image split conflicts | 0 |
| Polyvore item-ID split conflicts | 0 |
| Polyvore outfit-ID split conflicts | 0 |

No image, item, or outfit leakage was found in the provided handoff and generated splits.

## 12. Reproducibility

The exact split configuration is stored in:

`configs/m1_splits.yaml`

The exact item-to-split assignments are stored in:

`data/manifests/split_manifest.csv`

The configuration records:
- Random seed
- Splitting method for each dataset
- Stratification rule
- Grouping rules
- Source release information
- Input manifest SHA-256
- Input manifest dimensions
- Exact assignment manifest

The split manifest should be treated as immutable after verification. Any change to the raw manifest or split configuration should trigger split generation and leakage checks again.

## 13. Limitations

1. The current raw manifest does not contain Fashionpedia training/test records.
2. The current raw manifest does not contain Polyvore training/test records.
3. No missing source records were inferred or fabricated.
4. DeepFashion-MultiModal remains backup-only.
5. Cross-dataset category mappings were not created as part of M1.

## 14. Conclusion

The available M1 data was assigned to reproducible target splits without modifying the raw manifest.

Fashion-MNIST uses a deterministic stratified 90/10 train-validation split while preserving the official test set. Fashionpedia and Polyvore official validation splits were preserved.

Assignment completeness, count reconciliation, category coverage, and leakage checks all passed for the provided handoff.


## 14. Pre-Allocation Grouping Verification

Grouping rules were explicitly checked before/alongside split allocation:

- Fashion-MNIST: `item_id` used as the grouping unit.
  - 60,000 grouping units.
  - 0 groups containing multiple item IDs.
- Fashionpedia: `source_image_id` used as the grouping unit.
  - 1,158 image groups.
  - 0 image groups crossing target splits.
- Polyvore Outfits: `outfit_id` used as the grouping constraint.
  - 15,288 outfit groups.
  - 0 outfit groups crossing target splits.

Status: **PASS**

## 15. Immutable Evaluation Manifest

A separate evaluation manifest was created containing only the final test records:

`data/manifests/evaluation_manifest.csv`

- Records: **10,000**
- Unique items: **10,000**
- Duplicate item IDs: **0**
- Non-test records: **0**
- SHA-256: `84dbc08c1f4bfcf9459e35ce4a78bbf74ca9b324183c105b290e5c0b4ac3a6b5`

The evaluation manifest is marked immutable and reserved for final evaluation.

## 16. Test Data Isolation

The test/evaluation records are explicitly excluded from:

- Fitting preprocessing statistics
- Selecting augmentations
- Model tuning
- Model selection

The test set is reserved for final evaluation only.

The isolation policy is recorded in:

`configs/m1_splits.yaml`

## 17. Updated Deliverables

The M1 split outputs are now:

- `data/manifests/split_manifest.csv`
- `data/manifests/evaluation_manifest.csv`
- `configs/m1_splits.yaml`
- `docs/split_report.md`

The original `data/manifests/raw_manifest.csv` remains unchanged.

## 18. Final Status

All M1 split and evaluation-manifest checks that can be completed without Hana's derivative mapping have passed.

Hana's derivative mapping integration remains **pending** and has intentionally not been performed.
