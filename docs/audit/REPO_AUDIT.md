# Repository audit - Phase 0

Audit date: 2026-10-04. Baseline: `5f033d3`.

The working tree was clean on `main`. The first live PR/branch lookup was blocked
by network access. A subsequent lookup before Phase 1 confirmed only remote
`main` and no open pull requests.

## Baseline checks

- Manifest: 85,815 rows with 85,815 unique IDs; validation passed.
- Two existing manifest tests passed using unittest.
- Tracked Python files parsed without syntax errors.
- Pytest, Ruff, and Mypy were absent from normal system Python.
- Python 3.13.15 was observed; clean installation and other versions were unverified.

## MUST: Phases 1-3

- Four research scripts contain machine-specific paths; they are not portable.
- Seven Markdown link occurrences are broken after handoff documents were moved.
- M1 instructions reference absent `docs/dataset_mapping.md` and `docs/review_corrections.md`.
- Fashionpedia annotation JSON and Polyvore metadata/split JSON are not committed.
  Sample pictures do not supply the complete machine-readable annotation inputs.
- Manifest validation covers schema, IDs, source names, and nonempty content,
  but not dimensions, path resolution, annotation correctness, or leakage.
- No end-to-end preprocessing smoke test or implemented preprocessing loader exists.
- Five proposed environment variables are not consumed by code.
- Most research-script functions lack complete type hints; some scripts run on import.
- Preserve pyproject.toml as the existing dependency source of truth.
- A large-file policy must explicitly allow the existing 31,509,210-byte manifest.

## SHOULD: Phases 6-7

- CI currently covers Python 3.11 only and omits type/format/link/artifact checks.
- Handoff documentation retains temporary-ZIP wording.
- The original Polyvore report retains an older access-blocked assessment without
  clearly distinguishing it from subsequent approved-access evidence.
- M2-M5 documents lack explicit status and complete input/output acceptance contracts.

## COULD: Phases 4-5

- Milestone packages exist, but typed milestone contracts are not implemented.
- CODEOWNERS uses one account for all areas; backup reviewers are unspecified.
- No handoff-blocker issue template exists.

## Needs human

- Decide the code license independently of dataset terms.
- Confirm teammate GitHub handles, backup reviewers, and Asmaa's canonical name.
- Resolve public redistribution eligibility for committed dataset sample images.
- Obtain Ziad/Asmaa handoff review and owner approval of unresolved contracts.

No code, data, or configuration was edited during Phase 0. This document records
the audit after approval to proceed to Phase 1.
