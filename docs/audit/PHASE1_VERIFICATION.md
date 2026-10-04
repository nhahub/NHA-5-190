# Phase 1 - engineering baseline

Implemented on `chore/repo-hardening` after the project owner created the branch.

## Changes

- Normal-Python setup with minimal dev dependencies and optional data/ML extras.
- Cross-platform `python scripts/tasks.py <task>` quality commands.
- Ruff formatting/lint scope for shared code and validation entry points.
- Strict Mypy configuration for implemented `src/wardiq` code.
- Optional pre-commit checks and an explicit existing-manifest size exception.
- Planned environment variables are labeled as inactive; no dotenv behavior is claimed.
- Formatting corrections preserve existing validator behavior and test cases.

## Verification

Validated with normal Python 3.13.15. Tools were fetched as PyPI wheels, checked
against PyPI SHA-256 digests, and loaded through a temporary PYTHONPATH outside
the repository. No virtual environment was created and system packages were not
modified. This confirms tool execution, not a clean editable Pip installation.

- Manifest: 85,815 rows / 85,815 unique IDs; passed.
- Pytest 9.1.1: 2 tests passed.
- Ruff 0.16.10: lint passed; 11 scoped Python files already formatted.
- Mypy 1.20.2: no issues in 8 source files.
- Git whitespace check passed.
- No manifest, sample evidence, dataset decisions, or M1 handoff content changed.

## Limits and pending decisions

- Normal Pip installation still encounters temporary-folder permission failures.
- Python 3.10-3.12 clean installation remains for CI verification in later phases.
- Pre-commit hook installation/execution is not yet verified.
- License choice and dataset sample redistribution decisions remain with the owner.
- Historical research scripts stay outside the initial quality scope until Phase 3.
- Phase 2 and subsequent phases were not started.
