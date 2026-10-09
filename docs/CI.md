# Continuous integration

The workflow in `.github/workflows/ci.yml` runs on pull requests, pushes to `main`
and `chore/repo-hardening`, and manual dispatch. The quality matrix installs
`.[dev,data,ml,color]` and runs the same commands used locally with normal Python.
It uses PyTorch/torchvision for image-loader tests, but requires no raw dataset
download, trained model, secret or GPU execution.

The configured matrix is Python 3.10, 3.11, and 3.12 on Ubuntu. Each job has a
10-minute timeout, read-only repository permissions, and a dependency cache keyed
by `pyproject.toml`. A newer run cancels an older run for the same workflow/ref.

## Checks

Run from the repository root after installing `.[dev,data,ml,color]`:

```powershell
python scripts/tasks.py lint
python scripts/tasks.py format-check
python scripts/tasks.py typecheck
python scripts/tasks.py test
python scripts/tasks.py validate
python scripts/tasks.py links
python scripts/tasks.py clean-manifest
python scripts/tasks.py splits
python scripts/tasks.py taxonomy
python scripts/tasks.py duplicates
```

Lint and formatting cover shared package code, tests, and the validation helpers
listed in `scripts/tasks.py`. Historical research scripts are outside that lint
scope. Strict type checking covers `src/wardiq`. Tests cover repository helpers,
M1 loaders/garments/splits and the M2 color/attribute handoff components. Model training and evaluation
remain their owners' work.

Mypy uses the running interpreter's Python version. Each matrix job checks the
source and the dependency stubs installed for that interpreter. The Python 3.10
job verifies the declared minimum; later jobs verify their corresponding versions.
Forcing all jobs to target 3.10 makes mypy reject Python 3.12 syntax in newer NumPy
stubs installed by Python 3.12, even though the application imports successfully.
Use an environment containing dependencies for the target version when explicitly
checking another interpreter version. See [mypy platform configuration](https://mypy.readthedocs.io/en/stable/command_line.html#platform-configuration).

Repository validation checks required paths, the raw manifest, and the artifact
policy (including selected secret patterns). This is not a full secret scanner or
dataset license review. Data-bearing sample checks are a separate local command
with `.[data]`. The separate `M1 source samples` job installs `.[data,color]` on
Python 3.11, checks decoding/traceability/dimensions, prepares garment crops and
extracts M2 palettes and verifies the provisional attribute target/mask handoff.
It downloads no raw dataset and needs no PyTorch installation.

The quality matrix also regenerates the manifest-only clean output and checks
reference duplication. It verifies canonical assignments, official test isolation,
stratification counts and image/outfit identity leakage, and checks observed
taxonomy coverage. Generated files stay ignored. These checks do not establish
full image coverage, visual duplicate detection, taxonomy approval or final model
quality. See the [current sample pipeline](m1/run_pipeline.md).

To reproduce the source-sample job locally after installing `.[data,color]`:

```powershell
python scripts/tasks.py m1-images
python scripts/tasks.py samples
python scripts/tasks.py garments
python scripts/tasks.py colors
python scripts/tasks.py attributes
```

## Documentation links

`links` checks inline Markdown file/image paths in Git-tracked and nonignored
untracked Markdown files, excluding fenced code, URLs, and anchor-only links.
It checks file existence, not heading anchors, reference-style links, HTML links,
or remote websites. Root-relative paths resolve against the repository root.

`configs/ci/link-baseline.json` is now empty: Phase 7 repaired the seven broken
occurrences recorded in Phase 0. Any broken local link fails the check. Counted
exceptions, if ever explicitly approved, cannot grow silently; stale exceptions
also fail. The checker prints the remaining baseline count on every run.

## Verification and merge settings

Local and hosted results are recorded separately in the audit reports. Hosted
CI must pass for the exact pushed commit before declaring it green; local success
or a successful run on an earlier commit does not establish that result.

Required status checks and branch protection are repository settings. This phase
does not change them. An owner can select the three `Quality (Python ...)` jobs
as required checks after their first successful GitHub run.
