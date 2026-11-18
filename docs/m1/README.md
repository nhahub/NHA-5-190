# WARDIQ M1 — Taxonomy and Verification README

**Status:** early taxonomy handoff published (v0.1.0). Task stays **In Progress**. Final verification starts only after Hayat's integrated pipeline.

This file is kept up to date through M1. Sections marked *pending* are filled as each owner delivers.

## 1. Early handoff: taxonomy

| Item | Path |
|---|---|
| Versioned mapping and missing-value policy | `configs/m1/taxonomy.json` |
| Apply / coverage check | `scripts/apply_taxonomy.py` |
| Coverage evidence (one row per observed source category) | `reports/m1/taxonomy_coverage.csv` |

Reproduce the coverage check from the repository root:

```bash
python scripts/apply_taxonomy.py                      # uses data/manifests/clean_manifest.csv
python scripts/apply_taxonomy.py --manifest data/manifests/raw_manifest.csv
```

Loaders can import it:

```python
from scripts.apply_taxonomy import load_taxonomy, map_category
tax = load_taxonomy()
map_category(tax, "fashionpedia", 23)   # {'source_label': 'shoe', 'common_category': 'footwear', 'mapping_status': 'direct', ...}
```

### Common vocabulary (11 categories, proposed)

`top`, `bottom`, `one_piece`, `outerwear`, `footwear`, `bag`, `headwear`, `eyewear`, `scarf`, `jewellery`, `accessory_other`

### Mapping summary (observed labels only)

| Source | Observed categories | direct | approximate | ambiguous | unmapped | not_a_garment |
|---|---:|---:|---:|---:|---:|---:|
| Fashion-MNIST (smoke tests only) | 10 | 10 | 0 | 0 | 0 | 0 |
| Fashionpedia validation | 46 | 15 | 6 | 3 | 3 | 19 |
| Polyvore disjoint validation (127 fine ids → 11 groups) | 127 | 99 | 28 | 0 | 0 | 0 |

- **Fashionpedia ambiguous:** cardigan, vest, watch. **Unmapped:** leg warmer, tights/stockings, sock. **Not a garment:** the 19 part categories (ids 27–45), per the dataset decision.
- **Polyvore approximate:** `all-body`, `sunglasses`, `accessories` (contents not verified).
- **Coverage result:** every observed category id in the 85,815 retained manifest rows is present in the taxonomy (0 missing).

### Missing values (how code must represent them)

- Unavailable value → `null` in JSON/Python, empty cell in CSV, plus a `<field>_status` column.
- `unavailable_in_source`: the dataset has no such field (Polyvore and Fashion-MNIST attributes).
- `not_annotated`: the dataset has the field but this record has no value (a Fashionpedia annotation with empty `attribute_ids`). This is unknown, **never a negative**.
- Categories with no common mapping keep their source id and label; `common_category` is `null`.
- Default downstream use: `direct` and `approximate`. Strict use: `direct` only.

Examples with real item IDs are in `taxonomy.json` under `examples`.

## 2. Findings routed to owners

| # | Finding | Owner | Action |
|---|---|---|---|
| 1 | In `raw_manifest.csv` and `clean_manifest.csv`, Fashionpedia `category_ids` (sorted as text) and `category_labels` (sorted alphabetically) are separate sets. They line up position by position in only 63 of 1,158 rows. | Eyad, Ziad | Loaders must look labels up by id. Consider a note in `data/README.md` or a per-annotation export. |
| 2 | Polyvore fine-grained category names and the full Fashionpedia attribute list (294) are not in the handoff. Only 35 attribute names are verified. | Eyad | Provide `metadata.json` names and the official attribute list. |
| 3 | Handoff docs say no cross-dataset mapping in M1. The common vocabulary here is a proposal. | Project lead | Approve or reject; source labels stay authoritative meanwhile. |
| 4 | Fashionpedia id-to-name table is verified against the manifest and samples, not against the official JSON `categories`. | Eyad | Confirm when the JSON is shared. |

## 3. Owner outputs (pending)

| Owner | Output | Implementation / config | Output location | Limitations | Reproduction command |
|---|---|---|---|---|---|
| Eyad | Dataset selection, task mapping, samples | `docs/dataset_mapping.md` | `data/manifests/raw_manifest.csv` | Raw datasets not in handoff; Fashionpedia provisional | See `README_START_HERE.md` |
| Ziad | Data cleaning report | `scripts/03_validate_sample_images.py`, `scripts/04_duplicate_groups.py` | `data/manifests/clean_manifest.csv`, `reports/m1/data_quality.md` | Full image decode and near-duplicates pending | *to be added* |
| Hana | Crop policy | *pending* | *pending* | *pending* | *pending* |
| Omar | Split manifests | *pending* | *pending* | *pending* | *pending* |
| Hayat | Integrated loaders / pipeline | *pending* | *pending* | *pending* | *pending* |

## 4. Final verification (pending)

Runs after Hayat's integration. Results go to `reports/m1/verification.md`: stable IDs, source traceability, valid paths, mapped labels, explicit missingness, geometry, split membership, leakage evidence, crop/split consistency and loader counts.
