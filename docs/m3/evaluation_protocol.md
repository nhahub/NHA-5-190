# M3 evaluation: rule baseline versus Logistic Regression

**Status: protocol defined, no result yet.** The comparison needs two artifacts that are not in
the repository (see "What is needed to run it"). Any result produced from them is
**validation-only** and is not a final evaluation.

## What is compared

The transparent rule baseline (`src/wardiq/compatibility/rule_baseline.py`) and Ziad's Logistic
Regression ([handoff](../../M3_LOGISTIC_REGRESSION_HANDOFF.md)), scored on the **same validation
pairs**. The rule baseline reads the exported feature rows; the LR scores come from its
`validation_predictions.csv`. The script checks pair by pair that both files describe the same
population and stops if they do not.

## Protocol

| Item | Decision |
|---|---|
| Population | Validation pairs exported by `scripts/m3/build_pair_features.py`. The compared rows are the ones **both** methods can score. Rows the rule leaves unscored (too little evidence) are counted and listed as excluded, never dropped silently. |
| Labels | Positive: source-outfit co-occurrence. Negative: assumed category-preserving replacement, seed 42 ([data protocol](compatibility_data.md)). These are not human judgments. |
| Main metric | ROC-AUC. It needs no threshold, so it can be compared fairly between a score and a probability. |
| Thresholded metrics | Precision, recall, F1 and accuracy at one threshold per method. LR uses the threshold in its prediction file (chosen on validation). The rule uses the maximum-F1 threshold on the same validation rows. Both thresholds are fitted on the rows they are measured on, so these numbers are optimistic in the same way for both. |
| Calibration | LR only: Brier score and a 10-bin reliability table. The rule score is not a probability, so no calibration claim is made for it. |
| Ranking metrics | **Not reported.** Precision@K or NDCG@K need relevance labels and a candidate universe per query. The pair labels are not relevance judgments, and no such universe exists. `default_k` in `configs/m3/ocs.json` (5) is a demo default only. |
| Relevant pairs | Pair-level metrics use every labelled pair. Outfit-level OCS uses the category pairs proposed in `configs/m3/ocs.json` (to be agreed with Hana and Omar). |
| Counts and class balance | Reported for all rows and for the compared rows. |
| Failure cases | The 10 most confident false positives and 10 most confident false negatives of each method, with item IDs, plus a count of pairs where the methods agree or disagree. |
| Test split | Not used. The script refuses it. It may only be scored once, with the locked final configuration, after the protocol, splits and feature coverage are approved. Until then every result is labelled validation-only. |
| Targets | None. No numeric acceptance target is set, because the team has not approved one. |

## What is needed to run it

1. The validation feature export from Hayat: a directory with `features.npy`,
   `pair_inventory.csv` and `feature_schema.json` (see `hayat_artifact_handoff.md`).
2. The LR `validation_predictions.csv` for the same rows (kept in an ignored local directory,
   see the LR handoff; a team-accessible location is still needed).

```text
python scripts/m3/compare_rule_vs_lr.py --features-dir <feature export> --lr-predictions <validation_predictions.csv> --output <new directory>
python -m pytest tests/test_compare_rule_vs_lr.py
```

It writes `comparison_summary.json` (counts, exclusions, both methods' metrics, calibration,
agreement, input SHA-256) and `failure_cases.csv`. The output directory must be new, and a
repeat run gives identical files. Generated outputs stay out of Git.

## Results

None yet. For reference only, the LR handoff reports on **all** 67,869 validation pairs (owner
reported, not re-run here): ROC-AUC 0.6628, precision 0.5266, recall 0.9361, F1 0.6740 at
threshold 0.3168, Brier 0.2295. These are not on the compared population, and the handoff says the
available evidence does not establish calibration.

## Limitations

- Labels are provisional. A model can only be as good as these labels at telling pairs apart.
- Near-duplicate products across pairs have not been ruled out, which can inflate results.
- The LR handoff notes that reload equivalence was not verified.
- The rule score is a heuristic. Its weights and category rules are hand-set.
- The toy tests check the arithmetic, not the quality of either method.

## Open items

| Item | Owner |
|---|---|
| Team-accessible location for the validation feature export and LR predictions | Hayat and Ziad |
| Approve this protocol, the thresholds rule, and the relevant category pairs | Hana, Omar, Ziad and the lead |
| Near-duplicate and reload checks | Ziad and Hayat |
| Review of the M3-to-M4 packet | Hana and Asmaa |
