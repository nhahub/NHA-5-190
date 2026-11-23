# M3: Pairwise compatibility, OCS and Top-K

Owner: Hana. For Sunday review: Hana and Asmaa (M3 -> M4 contract), Omar (category pairs).

## What it does
1. Takes candidate outfits (list of items with a category).
2. Rejects invalid candidates, with a reason (see table).
3. Scores each relevant item pair with C(i, j), the compatible-probability from Ziad's model.
4. OCS = plain arithmetic mean of those pair scores. No weights.
5. Ranks outfits by OCS and returns the top K.

No training, calibration, weighting or second model here.

Code: `src/wardiq/compatibility/ocs.py` | Tests: `tests/test_ocs.py` | Config: `configs/m3/ocs.json`

## Commands
```bash
# build (pair_scores.json is a stand-in for Ziad's model until it is wired in)
python scripts/build_recommendations.py \
  --candidates docs/m3/sample/candidates.json --cache docs/m3/sample/cache_ids.json \
  --scores docs/m3/sample/pair_scores.json --model-version STUB --cache-version STUB \
  --k 5 --out docs/m3/example_output.json

# load + check against the contract
python scripts/load_recommendations.py docs/m3/example_output.json

# tests (25 passed)
pytest tests/test_ocs.py
```
`--k` is optional; the default is `default_k` in `configs/m3/ocs.json`.

## Rules
| Case | Result |
|---|---|
| Ranking | OCS high to low; ties go to the smaller `outfit_id`. Input order never matters. |
| K larger than available outfits | All outfits are returned. `requested_k` and `returned_k` show the difference. No padding, no error. |
| K below 1 | Error |
| Empty input | `top_k: []`, `returned_k: 0` |
| Fewer than 2 items / same item twice / an item not in the cache | Rejected: `too_few_items` / `repeated_item` / `item_not_in_cache` |
| Same outfit_id twice / same set of items as an earlier outfit | Rejected: `duplicate_outfit_id` / `duplicate_of:<outfit_id>` |
| No relevant pair in the outfit | Rejected: `no_relevant_pairs` |
| Every relevant pair was unscorable or invalid | Rejected: `failed` |
| Some pairs unscorable or probability invalid (NaN, <0, >1) | Pair listed in the outfit's `excluded`; `status: partial`; OCS is the mean of the rest |
| Item with no category | Listed in the outfit's `excluded`; the other items are still scored |
| Pair order | The model is always called with the two ids sorted, so (a, b) = (b, a) |

Nothing is dropped silently: every candidate is either in `top_k` or in `rejected` with a reason.

## Proposed M3 -> M4 output (`contract_version` 0.2.0)
```
contract_version   "0.2.0"
versions           {model, cache, config}      all required
calibration        {status: not_provided | evidence_attached, evidence: path or null}
requested_k, returned_k
top_k              [{rank, outfit_id, item_ids, ocs, status, pairs, excluded}]
                   pairs:    [{pair_id, item_a, item_b, score}]   <- the explanation
                   excluded: [{scope: item|pair, id, reason}]
rejected           [{outfit_id, reason}]
```
`validate_output()` checks it (versions, K counts, unique outfits, ranks, ordering, OCS range, pair scores present). Example: `docs/m3/example_output.json`.

## Plug in Ziad's model
Replace `prob` in `scripts/build_recommendations.py` with a function that returns his probability for two item ids (features from the chosen cache) and raises `ItemUnavailable` when an item has no features. Pass the real model and cache versions.

## Not done yet (honest status)
1. **No real eligible data yet.** The repo has no Ziad model and no feature cache, so the run above uses 5 stub candidates and made-up pair scores. Counts and metrics must be re-run on real data.
2. **Calibration is not claimed.** `calibration.status` stays `not_provided` until Ziad's evidence is attached.
3. **Category pairs in `configs/m3/ocs.json` are a proposal** for Omar and Asmaa to agree.
4. Tie rule, symmetry and contract 0.2.0 (bumped from 0.1.0 when ranking fields were added) are proposals for Sunday's review.
5. "Explanations" are the per-pair scores only; no other explanation source exists.
