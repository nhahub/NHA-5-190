# Continuous integration

The workflow in `.github/workflows/ci.yml` runs on pull requests, pushes to `main`
and `chore/repo-hardening`, and manual dispatch. It installs only `.[dev]` and runs
the same commands used locally with normal Python. No raw dataset, ML library,
trained model, secret, or GPU is required.

The configured matrix is Python 3.10, 3.11, and 3.12 on Ubuntu. Each job has a
10-minute timeout, read-only repository permissions, and a dependency cache keyed
by `pyproject.toml`. A newer run cancels an older run for the same workflow/ref.

## Checks

Run from the repository root after installing `.[dev]`:

```powershell
python scripts/tasks.py lint
python scripts/tasks.py format-check
python scripts/tasks.py typecheck
python scripts/tasks.py test
python scripts/tasks.py validate
python scripts/tasks.py links
```

Lint and formatting cover shared package code, tests, and the validation helpers
listed in `scripts/tasks.py`. Historical research scripts are outside that lint
scope. Strict type checking covers `src/wardiq`. Tests cover infrastructure;
teammate implementation and model evaluation remain their owners' work.

Repository validation checks required paths, the raw manifest, and the artifact
policy (including selected secret patterns). This is not a full secret scanner or
dataset license review. Data-bearing sample checks are a separate local command
with `.[data]`; they are not included in the dependency-light CI job.

## Documentation links

`links` checks inline Markdown file/image paths in Git-tracked and nonignored
untracked Markdown files, excluding fenced code, URLs, and anchor-only links.
It checks file existence, not heading anchors, reference-style links, HTML links,
or remote websites. Root-relative paths resolve against the repository root.

`configs/ci/link-baseline.json` records exactly seven existing broken occurrences
in the research decision documents from Phase 0. Those documents remain unchanged
during Phase 6. New broken links or additional occurrences fail the check. Once a
baseline link is repaired in Phase 7, remove its exception; stale exceptions fail.
The checker prints the remaining baseline count on every run.

## Verification and merge settings

Local Phase 6 verification used Windows and Python 3.13.15 with the previously
verified development-tool wheels. The configured Ubuntu matrix and clean pip
installation require a real GitHub run after these changes are pushed. Workflow
configuration alone does not mean CI has passed remotely.

Required status checks and branch protection are repository settings. This phase
does not change them. An owner can select the three `Quality (Python ...)` jobs
as required checks after their first successful GitHub run.
