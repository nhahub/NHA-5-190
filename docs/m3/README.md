# M3: Pairwise compatibility, OCS and Top-K

Owner: Hana. Reviewers: Asmaa (M3 -> M4 contract), Omar (category pairs).

## What this does
- Takes C(i, j), the compatible-probability from Ziad's saved Logistic Regression, as a function `prob_fn(item_a_id, item_b_id) -> float`.
- OCS = plain arithmetic mean of C(i, j) over the **relevant category pairs** in `configs/m3/ocs.json`. No weights.
- Top-K = outfits sorted by OCS, highest first.
- No training or calibration happens here.

Code: `src/wardiq/compatibility/ocs.py` · Tests: `tests/test_ocs.py` · Example payload: `docs/m3/example_output.json`

```bash
pytest tests/test_ocs.py            # 17 passed
python scripts/ocs_demo.py          # stub probabilities, prints the M3 -> M4 payload
```

## Rules
| Case | Result |
|---|---|
| Item has no category | listed in `excluded` (`item_unavailable`), never dropped silently |
| `prob_fn` raises `ItemUnavailable` | that pair is excluded (`item_unavailable`) |
| Probability is NaN, inf, <0, >1, not a number | that pair is excluded (`invalid_probability`) |
| Some pairs excluded, some scored | `status: partial`, OCS = mean of the scored pairs |
| No relevant pair exists | `ocs: null`, `status: no_relevant_pairs` |
| Relevant pairs exist but none usable | `ocs: null`, `status: failed` |
| Pair order | `prob_fn` is always called with the two ids sorted, so (a, b) = (b, a) |
| Ties in Top-K | smaller `outfit_id` first |

## M3 -> M4 payload (`contract_version` 0.1.0)
`contract_version`, `versions {model, cache, config}`, `calibration {status, evidence}`, `outfits [{outfit_id, item_ids, ocs, status, pairs [{pair_id, item_a, item_b, score}], excluded [{scope, id, reason}]}]`, `top_k [{rank, outfit_id, ocs}]`.
`validate_output()` checks it. `calibration.status` stays `not_provided` until Ziad's calibration evidence is attached.

## Plugging in Ziad's model
Wrap his saved model so it returns one probability for two item ids (looking features up in the feature cache) and raises `ItemUnavailable` when an item has no features. Pass it as `prob_fn`; pass real model/cache versions in `versions`.

## Still open (not decided by this PR)
1. Category pairs in `configs/m3/ocs.json` are a **proposal** - Omar/Asmaa to confirm.
2. Ziad's model version, interface and calibration evidence are not in the repo yet, so "calibrated probabilities" is **not** claimed.
3. Symmetry and the tie rule are my defaults - Asmaa to confirm.
4. Demo output uses stub scores only; no real metrics yet.
