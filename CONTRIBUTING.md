# Contributing to WARDIQ

## Branch workflow

Do not commit directly to `main`. Create a branch using `feat/<name>/<scope>`, `fix/<name>/<scope>`, `docs/<name>/<scope>`, or `exp/<name>/<scope>`. Example: `feat/ziad/clip-baseline`.

## Local setup

```powershell
python -m pip install -e ".[dev]"
python scripts/validate_repository.py
python -m pytest
```

## Quality commands

Use normal Python from the repository root:

```powershell
python scripts/tasks.py lint
python scripts/tasks.py format-check
python scripts/tasks.py typecheck
python scripts/tasks.py test
python scripts/tasks.py validate
```

`python scripts/tasks.py format` changes only the shared package, tests, and the
repository validation/task entry points. Historical research scripts and M1
evidence are excluded from this initial formatting scope.

Dependencies are defined in `pyproject.toml`; requirements files reference its
extras. Install `.[data]` for inspection scripts and `.[ml]` for model development.

Optional commit checks:

```powershell
python -m pre_commit run --all-files
python -m pre_commit install
```

Run hook installation yourself when Git metadata is writable. Hooks use the
already-installed normal Python tools. Source datasets and weights remain local.
The existing large manifest has a specific size-check exception; the exception
does not establish the manifest's correctness or allow other large files.

## Configuration and license

No Python code currently reads environment variables from `.env.example`.
Those entries are explicitly planned, not active configuration. No dotenv loader
is implemented. Configure research inputs through their documented script paths
until Phase 3 makes them portable.

The project owner must select the code license. Dataset access and redistribution
conditions remain separate; no code license grants rights to dataset images.

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
