# M3 transparent rule baseline (draft, pending Hana's review)

## Purpose (draft, pending Hana's review)

This baseline gives each item pair a small, explainable heuristic score. It
uses named signals from `PairFeatureBuilder`. It does not train a model and it
does not use attributes. Training attribute values are masked; missing
attributes must never be read as negative evidence.

## Signals and weights (draft, pending Hana's review)

| Signal | Weight | Feature read | Value |
| --- | ---: | --- | --- |
| Embedding | 0.25 | `clip:cosine` | Clip cosine to the range [0, 1]. |
| Colour | 0.35 | `lab:expected_delta_e76_over_100` | `1 - min(distance, 1.0)`. |
| Category | 0.40 | `category:both_mapped` and the active `category:<a>|<b>` column | Look up the pair in the category rules below. |

The score is the weighted average of available signals. The weights are
renormalised over only the signals that are available. `weight_coverage` is
the sum of their original weights. If coverage is below 0.5, the result has
`score = null` and `status = "insufficient_evidence"`. Otherwise status is
`"scored"`.

The category score uses this three-row rule table:

| Rule | Score | Applies when |
| --- | ---: | --- |
| Complementary | 1.0 | top+bottom, top+footwear, bottom+footwear, one_piece+footwear, or outerwear paired with top, bottom, one_piece or footwear. |
| Accessory | 0.7 | Either item is accessory_other, bag, eyewear, headwear, jewellery or scarf. |
| Same or conflicting | 0.3 | Same category twice, top+one_piece, or bottom+one_piece. |

A mapped category pair without a rule is an error; it is not assigned a
made-up score. The active category feature is found by its name, not by its
position in the feature row.

## Missing-value rules (draft, pending Hana's review)

1. **Embedding:** required and always used. A cosine of zero is a real zero
   similarity; it is not missing.
2. **Colour:** omitted when `lab:both_available` is 0. Its weight is not
   treated as zero or as negative evidence.
3. **Category:** omitted when `category:both_mapped` is 0. Its weight is not
   treated as zero or as negative evidence.

If only embedding is available, coverage is 0.25, below the 0.5 minimum, so
there is no score. Attributes are not a fallback: their training values are
masked and must never be interpreted as negative.

## Worked example (draft, pending Hana's review)

Suppose the embedding cosine is 0.8, the normalized colour distance is 0.4,
and the category pair is complementary. The three signal values are 0.8,
0.6 (`1 - 0.4`) and 1.0. All signals are available, so:

`score = (0.25 × 0.8 + 0.35 × 0.6 + 0.40 × 1.0) / 1.0 = 0.81`

If colour is missing, the score is renormalised over embedding and category:

`score = (0.25 × 0.8 + 0.40 × 1.0) / 0.65 = 0.9231`

The second result also reports `weight_coverage = 0.65` and omits `colour`
from `signals_used`.

## Meaning and limitations (draft, pending Hana's review)

The result is a heuristic score in [0, 1], not a probability. It is not
calibrated and must not be written into `PairwiseScore.probability`.

Colour uses distance only. For example, black and white can have a large LAB
distance and therefore receive a low colour score, even when the combination
may be visually intentional. The weights and category table are hand-set and
have not yet been reviewed or validated against human judgements. The score
must not be described as a measured fashion-compatibility probability.

## Draft outfit record for review with Hana (draft, pending Hana's review)

Every field and behaviour below is a draft, pending Hana's review. This is a
review example only; it does not change the shared contract.

- `outfit_id`: identifier for the candidate outfit. (draft, pending Hana's review)
- `item_ids`: ordered item identifiers in the outfit. (draft, pending Hana's review)
- `pairs`: pair identifiers plus `score`, `status`, `signals_used` and
  `weight_coverage` for each pair. (draft, pending Hana's review)
- `mean_ocs`: mean of pair scores, or `null` if any pair is unscored. (draft,
  pending Hana's review)
- `rank`: candidate rank assigned by the ranking stage. (draft, pending Hana's review)
- `versions`: feature, baseline and candidate-generation versions. (draft,
  pending Hana's review)
- If any pair is unscored, `mean_ocs` is `null`; do not average only the
  remaining pairs. (draft, pending Hana's review)
- If a candidate is structurally invalid, candidate generation rejects it;
  this baseline does not decide structural validity or assign its rank.
  (draft, pending Hana's review)

## Scope boundary (draft, pending Hana's review)

Candidate generation owns structural validity and rejection. This module only
scores pairs and computes the mean OCS when every pair has a score. It does not
generate outfits, choose Top-K, resolve ties or freeze the M3-to-M4 contract.
