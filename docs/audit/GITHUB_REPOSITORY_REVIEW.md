# GitHub repository review

Date: 2026-10-08. Repository: [nhahub/NHA-5-190](https://github.com/nhahub/NHA-5-190).
Initial reviewed head: `6a1c69c`. Ziad's `dabb8a7` attribute handoff arrived during
the review and was pulled with a fast-forward while retaining local fixes.
Final reviewed base: `dabb8a7d37a55881f1cc182e10cf22b81cf649dd` plus the uncommitted
corrections below. No review correction was committed or pushed by this audit.

## Hosted state and evidence

All ten inspected pull requests were merged; no open PRs or issues were returned.
The inspected task branches contain merged work. `main` is not protected and the
repository returned no rulesets. These settings were not changed. For future
merges, the repository owner can require the quality matrix and sample job so
failed checks cannot be bypassed by a direct push. Existing merged PR #8/#9 bodies
still contain the unfilled template; the code verification is documented in the
repository audit reports rather than those descriptions.

The initial [CI run on 6a1c69c](https://github.com/nhahub/NHA-5-190/actions/runs/37779878854)
and latest [CI run on dabb8a7](https://github.com/nhahub/NHA-5-190/actions/runs/37781546164)
both showed:

| Job | Hosted result before these corrections |
|---|---|
| Quality (Python 3.10) | Passed |
| Quality (Python 3.11) | Passed |
| Quality (Python 3.12) | Failed at type checking; remaining quality steps skipped |
| M1 source samples | Passed, including garment and color commands |

The failing job used mypy 1.20.2 and newer NumPy stubs. Its diagnostic was
`numpy/__init__.pyi:737: Type statement is only supported in Python 3.12 and greater`.
The package was checked with a forced Python 3.10 target even in the 3.12 job.
The same failure was reproduced locally using mypy 1.20.2 and NumPy 2.5.3.

## Corrections

| Finding | Correction |
|---|---|
| Forced mypy 3.10 target rejected dependency stubs installed for 3.12 | Use the running interpreter's target; the 3.10 matrix job still verifies the declared minimum. Strict checking remains enabled. |
| Large negative bbox dimensions could overflow before fallback | Reject nonpositive dimensions before computing bbox edges; verify fallback and strict-failure policies. |
| Taxonomy CLI could overwrite protected committed evidence through output overrides | Apply the shared evidence guard to both coverage and mapped outputs. |
| Setup/CI docs and M2 ownership/status were stale | Match dependency installation, actual commands, provisional component status and the previously Notion-reconciled assignments. |
| Attribute validator printed FAIL but returned success | Return nonzero for invalid vectors/masks, identities, versions, metadata and counts; short vectors fail cleanly. |
| Attribute vocabulary order was not verified | Check contiguous vector indices, unique nonnegative IDs, source identity and declared ascending order. |
| Attribute report/config generators overwrote committed evidence and executed on import | Add portable CLI arguments/main guards and default to ignored artifacts. Refuse protected/report/input overwrites. |
| Untrained sample emitted null scores that contradicted its schema declaration | Document scores as nullable when no trained model/checkpoint is available. No scores are fabricated. |
| Attribute commands were outside the shared lint/test/CI pipeline | Add `python scripts/tasks.py attributes`, source-sample CI coverage, pre-commit scope and focused regressions. |
| Attribute handoff Markdown was escaped and encoded incorrectly | Restore readable headings/tables and link current reproduction instructions. |

The original attribute validator was tested with a deliberately incorrect mask
in an ignored temporary copy: it printed `status = FAIL` and returned exit code
zero. The corrected validator rejects this and other corruptions with exit code
one, without a traceback or modifying the source evidence.

## Local verification after corrections

- Full suite: **105 tests passed; 6 subtests passed**.
- Ruff lint/formatting, strict package types, repository/artifact checks, local
  documentation links and whitespace checks passed.
- Mypy 1.20.2 passed after the configuration fix, including a fresh explicit
  `--python-version 3.12` check. This is not a Python 3.12 runtime test.
- Canonical splits: 85,815 unique source IDs with exact assignment coverage,
  official test isolation and no image/outfit identity conflicts.
- M2 color: 56 input rows, 18 successful, 38 intentionally excluded, zero failed.
- Attribute handoff: 46 annotations, 35 verified vocabulary labels, 87 observed
  positive positions, 1,523 unknown positions and zero known negatives.
  All inference support remains zero; scores/checkpoint/thresholds are unavailable.
- Attribute exports repeat byte-for-byte in the same environment and preserve
  committed report evidence. Source, vocabulary, implementation and output hashes
  are recorded in `artifacts/m2/attributes/v1/attribute_handoff_report.json`.

Local verification used Windows/Python 3.13 and the available dependency toolkit,
with the exact hosted mypy version isolated under ignored `.local-check-tools/`.
One harmless joblib physical-core detection warning occurred during tests.
No raw data, generated feature output or local tool dependency was added to Git.

## Remaining boundaries

These changes must be pushed and the resulting exact-commit CI run must pass
before calling GitHub green. Full raw-image decoding/training is not verified:
the checkout has the committed development samples, not all source images.
Fashionpedia training data and explicit training-label support are still absent.
The attribute configuration declares a planned model/loss/threshold protocol;
no trained predictor or empirical metrics were supplied. The final M2 item/cache
contract and remaining category/embedding components still require their owners.

Reproduce using [the M1/sample pipeline](../m1/run_pipeline.md),
[the color handoff](../m2/color_extraction.md) and
[the current attribute handoff](../m2/attributes.md).
