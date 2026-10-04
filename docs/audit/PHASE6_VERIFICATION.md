# Phase 6 verification

Baseline: `6ae663f`, branch `chore/repo-hardening`, 2026-10-04.
The working tree was clean before editing. A live GitHub API lookup confirmed
no open pull requests and only the remote `main` branch.

## Changes

- Expanded the existing workflow to Python 3.10, 3.11, and 3.12.
- Added format, strict package type, and local documentation link gates.
- Routed existing lint, tests, structure/manifest, and artifact checks through
  the shared normal-Python task runner.
- Added manual dispatch, hardening-branch pushes, cancellation of superseded runs,
  and explicit pip cache dependency inputs; retained read-only permissions/timeouts.
- Added a counted seven-occurrence legacy link baseline pending Phase 7 repairs.
- Added three regression tests for link extraction and exception growth/cleanup.

## Verified locally

- 17 tests and six subtests passed on Python 3.13.15.
- Shared-code lint, format check, and strict package type checking passed.
- Repository validation passed for the unchanged 85,815-row manifest and artifact policy.
- Local Markdown link check passed with seven explicitly recorded legacy occurrences.
- Workflow YAML parsed and the matrix/check commands were inspected.
- `git diff --check` passed; research evidence, manifests, samples, and team modules
  were not changed.

## Needs human / remote verification

- Commit/push the changes and verify the real GitHub Ubuntu/Python matrix. Local
  checks used existing tool wheels, not a fresh pip install or alternate runtimes.
- Repository owners decide required status checks and branch protection.
- The existing license, sample redistribution, reviewer identity, and dataset
  handoff decisions remain unresolved as listed in the Phase 0 audit.
