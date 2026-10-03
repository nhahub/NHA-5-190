# Contributing to WARDIQ

## Branch workflow

Do not commit directly to `main`. Create a branch using `feat/<name>/<scope>`, `fix/<name>/<scope>`, `docs/<name>/<scope>`, or `exp/<name>/<scope>`. Example: `feat/ziad/clip-baseline`.

## Local setup

```powershell
python -m pip install -e ".[dev,data]"
python scripts/validate_repository.py
pytest
```

## Pull requests

Every pull request states the task and milestone, input/output contracts, validation commands, data or reproducibility limitations, and downstream reviewer. Use `Closes #<issue>` when it completes an issue. CI must pass before merge.

## Data and artifact rules

- Never commit full raw datasets, credentials, environment files, model checkpoints, or experiment caches.
- Commit only small representative samples allowed by the source conditions.
- Keep source data unchanged under `data/raw/<dataset>/`.
- Write generated data under `data/processed/` and record the producing configuration.
- Preserve source IDs and split names. Never fabricate a missing label, box, mask, attribute, or preference.
- Add a dataset to `data/README.md` and `configs/datasets/` before using it.

## Definition of done

A task is done when its output is reproducible, documented, checked where the shared contract can break, and usable by its downstream owner.
