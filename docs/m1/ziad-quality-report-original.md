# Preserved Ziad M1 quality report

Historical report from merged PR #2. The runnable follow-up and corrected label handling
are documented in [quality handoff](quality-handoff.md). Its reproduction claims are
not evidence that the original ZIP included a clean-manifest generator. The new
manifest-only outputs must not be treated as full image or geometry validation.

# WARDIQ — Milestone 1 Data Quality Report

## 1. Scope

Owner: Ziad Nasser  
Execution: 2 — Dataset Inspection & Quality Analysis / Cleaning  
Milestone window: 20–26 September 2026

This inspection uses the upstream raw manifest and the representative dataset samples included in the temporary handoff package.

The current manifest contains 85,815 unique image records:
- Fashion-MNIST: 70,000
- Fashionpedia validation: 1,158
- Polyvore Outfits disjoint validation: 14,657

The complete raw dataset files are not present in the temporary handoff. Therefore, full image-level decode/path validation cannot be claimed for all 85,815 records.

---

## 2. Manifest Integrity

### Identity checks

- Total manifest rows: 85,815
- Unique item IDs: 85,815
- Duplicate item IDs: 0
- Duplicate source identity records: 0
- Duplicate source image IDs: 0
- Exact duplicate rows: 0
- Duplicate original image references: 0

The manifest therefore contains no detected structural duplicates.

---

## 3. Dataset Counts

| Dataset | Records |
|---|---:|
| Fashion-MNIST | 70,000 |
| Fashionpedia | 1,158 |
| Polyvore Outfits | 14,657 |
| **Total** | **85,815** |

### Splits

| Dataset | Split | Records |
|---|---|---:|
| Fashion-MNIST | train | 60,000 |
| Fashion-MNIST | test | 10,000 |
| Fashionpedia | validation | 1,158 |
| Polyvore Outfits | disjoint validation | 14,657 |

---

## 4. Fashion-MNIST

- 70,000 manifest records.
- 28×28 grayscale source representation according to the dataset mapping.
- 10 classes.
- Class distribution is balanced at 7,000 examples per class.
- No annotation IDs are expected because Fashion-MNIST is represented through class labels rather than object-level annotations in this manifest.

Five representative sample images were inspected and decoded successfully.

The sample PNG files are 280×280 grayscale previews. They should not be interpreted as evidence that the original Fashion-MNIST source resolution is 280×280.

---

## 5. Fashionpedia

### Manifest statistics

- Images: 1,158
- Total annotation IDs: 8,781
- Images with zero annotations: 0
- Images with annotations: 1,158
- Mean annotations/image: 7.58
- Median annotations/image: 7
- Minimum annotations/image: 1
- Maximum annotations/image: 27

### Category fields

- Mean category IDs/image: 5.58
- Minimum: 1
- Maximum: 15
- No rows contain annotations while missing category IDs.
- No empty tokens were detected in annotation IDs or category IDs.

### Attribute fields

All 1,158 manifest rows contain attribute IDs.

This is image-level manifest coverage and should not be interpreted as annotation-level attribute coverage.

The upstream validation reported attributes on 5,259 of 8,781 annotations, corresponding to 59.89% annotation-level attribute coverage.

### Sample validation

Five Fashionpedia images were inspected.

For the five inspected samples:
- Images were available and decoded.
- Annotation counts were 12, 14, 4, 12, and 4.
- Mask counts matched the annotation counts.
- Category assignments were available for all inspected samples.

---

## 6. Polyvore Outfits

- 14,657 records.
- Disjoint validation subset.
- 300×300 RGB item images in the inspected samples.
- Five representative images were decoded successfully.
- Five sample records matched their item IDs, metadata labels, semantic categories, and outfit membership.

Four of the five inspected records did not have a description available. This is treated as missing metadata, not as an invalid image.

---

## 7. Image Path / Availability Limitation

Direct filesystem existence checks found no local source file for the 85,815 manifest references.

This does not mean that all 85,815 records are invalid.

Fashion-MNIST references use an archive/index representation such as:

data/raw/fashion_mnist/train-images-idx3-ubyte.gz::index=0

The temporary handoff also contains representative sample files rather than the complete raw datasets.

Therefore:

- Raw manifest records are retained.
- Missing local source files are not treated as semantic/image corruption.
- Full image-level validation remains pending until the actual source datasets are available.
- Representative samples were validated separately.

---

## 8. Duplicate Analysis

No exact duplicate manifest rows were found.

No duplicate original image references were found.

duplicate_groups.csv contains zero groups.

This analysis detects manifest/reference-level duplication only. It does not prove that no visually identical or near-duplicate images exist.

Visual/semantic duplicate detection requires access to the actual image collection and is therefore left for a later stage.

---

## 9. Cleaning Policy

The following rules were applied:

1. Preserve the raw manifest unchanged.
2. Do not delete or modify raw dataset files.
3. Do not infer or invent missing annotations.
4. Dataset-specific missing fields are not automatically treated as errors.
5. Missing attributes or descriptions remain explicitly unavailable.
6. Suspicious semantic labels should be flagged for review rather than silently corrected.
7. Records are excluded only when a reproducible validation rule demonstrates that the record is unusable for the intended task.
8. Because the full raw images are not available in this handoff, no manifest records are excluded solely because their source files cannot currently be opened locally.
9. Duplicate analysis is kept separate from semantic/visual duplicate analysis.

---

## 10. Cleaning Result

Raw manifest records: 85,815

Retained: 85,815

Excluded: 0

The clean manifest therefore currently contains the same item set as the raw manifest, with additional cleaning-status fields documenting the validation scope.

---

## 11. Reproducibility

The cleaning process is based on deterministic manifest checks.

The same raw manifest and validation configuration should produce the same retained item set.

Full image decode validation must be rerun after the actual source datasets are made available.

---

## 12. Handoff Status

### Ready

- Clean manifest generated.
- Duplicate group file generated.
- Manifest structural checks completed.
- Representative samples decoded successfully.
- Dataset-specific missing fields documented.
- Cleaning policy documented.

### Pending

- Full source image availability.
- Full-dataset image decode validation.
- Full visual/near-duplicate analysis.
- Review of suspicious semantic labels by the relevant task owner.


### Reproducibility validation

The cleaning result was rechecked against the same raw manifest.

- Same item ordering: PASS
- Same item set: PASS
- Same row count: PASS
- Reproducibility check: PASS

The accepted item set is therefore deterministic for the current input/configuration.
