# WARDIQ

WARDIQ is a six-week AI/ML project for clothing understanding, outfit compatibility, personalized recommendation, and wardrobe optimization. This repository is the shared implementation and handoff point for the six-person team.

## Current status

Milestone 1 data foundation is ready for team review. The repository includes a validated 85,815-row image manifest, verified development samples, dataset decisions, and reproducibility scripts. Large source datasets are intentionally excluded.

- **Fashionpedia:** provisionally selected for garment boxes, masks, categories, and attributes.
- **Polyvore Outfits:** selected for compatibility and recommendation using the disjoint split.
- **Fashion-MNIST:** used only for loader and preprocessing checks.
- **DeepFashion-MultiModal:** backup dataset.

Start with [the M1 handoff](docs/milestones/M1-data-handoff.md), [data instructions](data/README.md), and [dataset decisions](docs/decisions/dataset-selection.md).

## System flow

```mermaid
flowchart LR
    A[Raw images and annotations] --> B[M1 data pipeline]
    B --> C[M2 clothing understanding]
    C --> D[Structured item representation]
    D --> E[M3 compatibility and Top-K]
    E --> F[M4 personalization and context]
    F --> G[Wardrobe gaps and WUS]
    G --> H[M5 evaluation and demo]
```

## Quick start

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev,data]"
python scripts/validate_repository.py
pytest
```

Install the optional ML stack only when model work begins:

```powershell
python -m pip install -e ".[ml]"
```

## Repository map

| Path | Purpose |
|---|---|
| `configs/` | Versioned dataset, split, and model configuration |
| `data/manifests/` | Traceable image-level inventories committed to Git |
| `data/samples/` | Small verified examples for loader development |
| `data/raw/` | Local source downloads; ignored by Git |
| `data/processed/` | Generated artifacts; ignored by Git |
| `docs/` | Proposal, architecture, decisions, milestones, and ownership |
| `scripts/` | Reproducible download, inspection, and validation commands |
| `src/wardiq/` | Production Python package organized by system module |
| `tests/` | Fast checks for shared contracts and utilities |

## Team ownership

| Member | Primary responsibility |
|---|---|
| Eyad Amir | Data and CV pipeline |
| Hayat Hussein | CV representation and integration |
| Ziad Nasser | Computer vision and models |
| Omar Ahmed | Compatibility and recommendation |
| Hana Emad El Din Shazly | Personalization and optimization |
| Asmaa Tamer | Evaluation, documentation, and integration |

Detailed weekly assignments are in [team ownership](docs/team/OWNERSHIP.md).

## Collaboration rules

1. Create a short-lived branch from `main`.
2. Keep raw datasets and generated model weights out of Git.
3. Preserve `item_id`, source dataset, original path or index, annotations, and split metadata.
4. Open a pull request and request review from the downstream owner.
5. Merge only after CI passes and the documented output contract is satisfied.

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch names, commits, reviews, and data rules.

## Project boundary

The core deliverable is a reproducible AI/ML pipeline and evaluation. A full web/mobile application, marketplace integration, LLM assistant, RAG system, and virtual try-on are outside the six-week scope.
