## Problem and result

M3 task "Evaluate compatibility and ranking models". Adds the evaluation protocol
(`docs/m3/evaluation_protocol.md`) and a small command that compares the rule baseline with the
Logistic Regression on the same validation pairs: counts and exclusions, class balance, ROC-AUC,
thresholded precision/recall/F1, LR calibration, failure cases and method agreement. No result on
real data yet: the validation feature export and the LR prediction file are not in the repository.
Results will be labelled validation-only; the test split is refused.

## Milestone and owner

- Milestone: M3
- Task owner: evaluation of the compatibility and ranking models
- Downstream reviewer: Hana (M3-to-M4 packet), Ziad (LR), Hayat (features)

## Contract changes

None.

## Validation

- [x] `python scripts/validate_repository.py`
- [x] `pytest` (5 new tests with hand-calculated expectations; lint, format-check, links and artifact policy pass)
- [ ] Relevant dataset/model command and concise result recorded: not yet, waiting for the artifacts above

## Data and reproducibility

- [x] No raw dataset, credential, cache, or model weight was committed.
- [x] Dataset release, split, seed, and configuration are recorded (the command writes input SHA-256 values; labels follow the documented seed-42 protocol).
- [x] Missing labels remain missing and use masks/status fields (rows the rule cannot score are counted as excluded, never dropped silently).

## Evidence

- Metric helpers match hand calculations (ROC-AUC 13/16, precision 3/5, recall 3/4, F1 2/3, Brier).
- Toy population: 10 rows, 2 excluded for the rule, compared rows 8; runs are byte-identical and an
  existing output is never overwritten; a different population or the test split is refused.
- Limitations: labels are provisional (co-occurrence and assumed negatives); no ranking metrics
  because there are no relevance labels or candidate universe; near-duplicate leakage and LR
  reload equivalence are unverified; thresholded numbers are optimistic equally for both methods.
