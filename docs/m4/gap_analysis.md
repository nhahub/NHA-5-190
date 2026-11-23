# Milestone 4: Wardrobe Gap Analysis

**Owner:** Omar Ahmed  
**Module:** `src/wardiq/personalization/gap_analysis.py`  
**Config:** `configs/m4/gap_analysis_v1.json` (`wardiq.m4.gap-analysis-config.v1`, v1.0.0)  
**Tests:** `tests/test_gap_analysis.py`  
**Parent Spec:** [M4 - Personalization, context, and wardrobe optimization](../milestones/M4.md)

---

## 1. Overview & Method

Wardrobe Gap Analysis identifies missing or underrepresented clothing categories/items in a user's structured wardrobe by **simulating candidate additions** over M3's outfit candidate generation (`generate_candidates`) and compatibility scoring (`score_outfit_candidate`).

1. **Baseline Evaluation:** Runs M3 candidate generation on the user's current wardrobe to establish baseline feasible and useful outfit counts.
2. **Missing-Category Detection:** Compares the wardrobe's present categories against the 6 M3 template-active categories (`top`, `bottom`, `one_piece`, `outerwear`, `footwear`, `bag`). If no explicit `candidate_pool` is supplied, one synthetic candidate is generated per missing template-active category.
3. **Invalid-Category Filtering:** Any candidate whose `common_category` is outside M3's 11-category `category_vocabulary` (or `None`) is rejected with `invalid_category`.
4. **Redundancy Check:** Flags candidates that match an existing wardrobe item via:
   - Exact `item_id` match (`exact_item_id_match`)
   - Same-category embedding cosine similarity $\ge 0.85$ (`high_embedding_similarity`)
   - Same-category attribute Jaccard overlap $\ge 0.80$ (`high_attribute_overlap`)
   - Category count $\ge 3$ (`category_saturated`)
5. **Simulated Addition & Compatibility Evidence:** Adds each non-duplicate candidate to the wardrobe, identifies newly unlocked M3 outfits containing that candidate, and counts **useful** combinations (`ocs >= 0.5` when embeddings are provided; structural validity when embeddings are absent).
6. **Deterministic Ranking:** Ranks non-redundant candidates with positive incremental useful combinations using:
   - With embeddings: `gap_score = 0.6 * normalized_gain + 0.4 * avg_ocs - 0.5 * redundancy_score`
   - Structural only: `gap_score = normalized_gain - 0.5 * redundancy_score`
   - Deterministic tie-breakers: `incremental_useful_combinations` (desc), `avg_ocs` (desc), `redundancy_score` (asc), `candidate_category` (asc), `candidate_item_id` (asc).

---

## 2. Output Schema (`wardiq.m4.gap-analysis-result.v1`)

`WardrobeGapAnalysisResult.to_dict()` returns a JSON-serializable dictionary with:

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | `"wardiq.m4.gap-analysis-result.v1"` |
| `config_version` | `string` | Version of `gap_analysis_v1.json` (e.g., `"1.0.0"`) |
| `config_ref` | `string` | Traceable config reference (`configs/m4/gap_analysis_v1.json@1.0.0`) |
| `wardrobe_ref` | `string` | Identifier for the baseline wardrobe |
| `baseline_item_count` | `int` | Number of items in the baseline wardrobe |
| `baseline_feasible_combinations` | `int` | M3 structurally valid outfits before additions |
| `baseline_useful_combinations` | `int` | Baseline outfits meeting `min_useful_ocs` |
| `missing_categories` | `list[str]` | Template-active categories absent from the wardrobe |
| `has_meaningful_gap` | `bool` | `true` if at least one non-redundant candidate unlocks useful combinations |
| `ranked_gaps` | `list[dict]` | Ranked `GapCandidateRecord` objects with `evidence`, `redundancy`, and `explanation` |
| `redundant_candidates` | `list[dict]` | Candidates separated due to redundancy flags |
| `rejected_candidates` | `list[dict]` | Candidates rejected for `invalid_category` or `zero_incremental_useful_combinations` |
| `wus_handoff` | `list[dict]` | `wardiq.wardrobe-utility.v1` records for Hana's WUS engine |
| `product_matching_records` | `list[dict]` | `wardiq.m4.gap-candidate-product-record.v1` records for Asmaa/Hayat |

---

## 3. Team Handoff Contracts

### Hana (WUS Calculation)
Each ranked gap candidate exposes `to_wus_handoff()` matching `contracts.WardrobeUtility` (`wardiq.wardrobe-utility.v1`):
- **Populated:** `wardrobe_ref`, `candidate_item_id`, `gain` (incremental useful combinations), `avg_ocs`, `redundancy` (`redundancy_score` in `[0.0, 1.0]`), `config_ref`.
- **Explicitly `None` (never fabricated):** `preference`, `context`, `wus`.

### Hayat & Asmaa (Product-Matching-Ready Output)
Each ranked gap candidate exposes `to_product_matching_record()` (`wardiq.m4.gap-candidate-product-record.v1`) containing `rank`, `candidate_item_id`, `target_category`, `is_synthetic_candidate`, `gap_score`, `incremental_useful_combinations`, `avg_ocs`, `unlocked_templates`, `redundancy_score`, and `explanation`—without any marketplace integration.

---

## 4. Assumptions & Limitations

- **Single-Item Simulation:** Candidates are simulated one at a time against the baseline wardrobe; multi-item bundle synergies (e.g., adding both a top and a bottom simultaneously to an empty wardrobe) are not evaluated.
- **Template-Driven Detection:** Automatic missing-category synthesis targets the 6 M3 template-active categories (`top`, `bottom`, `one_piece`, `outerwear`, `footwear`, `bag`). Non-template accessories (`headwear`, `eyewear`, `scarf`, `jewellery`, `accessory_other`) are valid in the taxonomy but unlock 0 M3 template combinations.
- **No Fabricated Signals:** When embeddings are omitted, `scoring_mode` is `"structural_only"` and `avg_ocs` is `None`. Preference and context signals are never defaulted or fabricated.
- **Provisional Thresholds:** `min_useful_ocs = 0.5`, `embedding_similarity_threshold = 0.85`, `attribute_overlap_threshold = 0.8`, `max_category_saturation = 3`, and ranking weights (`0.6 / 0.4 / 0.5`) are versioned in `configs/m4/gap_analysis_v1.json` and remain configurable for M4 integration review.