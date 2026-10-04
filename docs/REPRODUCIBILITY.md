# Reproducing Eyad's M1 research

These commands reproduce existing dataset inventory and inspection work. They do
not implement the team's loaders, preprocessing, splitting, cropping, taxonomy,
models, or model evaluation. Run them with normal Python from the repository root.

## Checks that need no raw downloads

```powershell
python -m pip install -e ".[dev,data]"
python scripts/validate_repository.py
python -m pytest
python scripts/tasks.py samples
```

The sample check opens 15 committed source samples twice, resolves them to the raw
manifest, checks display dimensions, and compares decoded pixel hashes. It takes
under 60 seconds on CPU (0.644 seconds in the local verification). It is not a
preprocessing or leakage test. Fashion-MNIST samples are 280x280 enlarged previews
of 28x28 source images; use native IDX data for the actual pipeline.

Some historical sample-manifest paths refer to preview/original subdirectories
that were flattened in the handoff. Those existing manifests remain preserved.
The smoke check resolves the actual committed filenames against raw-manifest IDs.

## Configuration and command-line overrides

Versioned defaults are in `configs/research/m1.json`. Paths in its sections resolve
relative to the repository root, including when a command runs from another
directory. An alternate configuration file must have the same schema version and
the section for the command being run.

Each command supports `--help`, `--config`, and explicit input/output overrides.
For example:

```powershell
python scripts/export_fashion_mnist_samples.py --data-dir "D:/my-data/fashion_mnist"
python scripts/extract_polyvore_samples.py --source "D:/my-data/0000.parquet"
```

Generated outputs default to ignored `artifacts/m1/`. Commands refuse output paths
inside committed manifests, sample evidence, documentation, configs, or source.
Rerunning a command may replace files in its generated artifact directory. Raw
input files and committed evidence are preserved. Downloading an invalid existing
Fashion-MNIST archive now stops for review rather than deleting it automatically.

The default source URLs, checksum values, label vocabulary, and historical visual
observations remain in the existing scripts. CLI configuration controls source
paths and inspection counts/scales. No random sampling is used: IDX and parquet
samples use their first rows; Fashionpedia uses eligible JSON order; the manifest
uses the existing deterministic source ordering. No unused seed utility is added.

## Required raw inputs

| Dataset | Required local files | Access |
|---|---|---|
| Fashion-MNIST | Four official train/test IDX gzip files; sample export also uses their extracted IDX counterparts | [Official repository](https://github.com/zalandoresearch/fashion-mnist) |
| Fashionpedia | `val_test2020.zip`, `instances_attributes_val2020.json` | [Official download instructions](https://github.com/cvdfoundation/fashionpedia#download) |
| Polyvore Outfits | disjoint validation parquet, `metadata.json`, `disjoint/valid.json` | [Approved gated access](https://huggingface.co/datasets/mvasil/polyvore-outfits) |
| Original Polyvore | train/valid/test `*_no_dup.json`, `fill_in_blank_test.json`, `fashion_compatibility_prediction.txt`, `category_id.txt` | [Original repository](https://github.com/xthan/polyvore-dataset) |

Use the canonical directories listed in the versioned configuration, or pass
explicit overrides. Manifest reference strings preserve the canonical convention;
overrides point the research command at local inputs without rewriting source IDs
or the published directory convention. A referenced file still needs to be made
available to each teammate. No raw dataset is included in Git.

## Reproduction with canonical input paths

```powershell
python scripts/download_fashion_mnist.py
python scripts/export_fashion_mnist_samples.py
python scripts/inspect_fashionpedia_samples.py
python scripts/extract_polyvore_samples.py
python scripts/build_polyvore_check_report.py
python scripts/build_raw_manifest.py
python scripts/compare_manifest.py
python scripts/validate_polyvore_original.py
```

The Polyvore report is restricted to the original five checked item IDs and
refuses a parquet whose first five IDs differ. It rechecks metadata/membership
and calculates the current file checksum/count. Its visual descriptions are
historical human observations, not fresh automated visual judgments.

The original Polyvore script checks outfit-position reference overlap; those
references are not product identity and do not prove product-level disjointness.
The newer disjoint-validation file alone cannot prove cross-split leakage freedom.
Full split design and leakage validation remain Omar's assigned work.

## Successful research-run records

Commands using `research_cli.run` append successful run records to ignored
`artifacts/research_runs/runs.jsonl`. The schema is committed at
`configs/research/run-record.schema.json`. Records include command arguments,
configuration checksum, timestamp, Git commit, and dirty-working-tree status.
They do not claim a dirty run is reproducible from the commit alone. These local
records can contain local input paths; they are not published automatically.
Failed commands exit nonzero and are not logged as successful. The sample smoke
check prints its results without producing a run record.

## Verified locally during Phase 3

- All seven original commands display help and accept portable inputs.
- Existing Fashion-MNIST files passed checksum verification; a fresh network
  download was not repeated.
- Fashion-MNIST export reproduced five native images and enlarged previews.
- Fashionpedia inspection reproduced the original five image IDs and 46 annotation rows.
- Polyvore extraction/report rechecked the original five items and 14,657-row input.
- Full manifest regeneration produced 70,000 Fashion-MNIST, 1,158 Fashionpedia,
  and 14,657 Polyvore records: 85,815 total, matching preserved evidence exactly.
- LF-normalized manifest SHA-256:
  `84135923763f5fec09471435c0f292730ac19715e6c491d16aceea17f6cca99e`.
- Original Polyvore checks were rerun. They reported 98 FITB answer-index versus
  blank-position differences; interpretation requires dataset-owner review.

These checks used the owner's already-downloaded inputs via explicit CLI overrides.
A local run used Python 3.13.15, Pillow 12.3.0, and PyArrow 25.0.1. The optional
PyArrow upper bound was expanded to include this actually verified version;
older declared versions were not separately exercised.
A teammate must acquire the same inputs. Clean-install CI, full-dataset leakage,
training-annotation verification, and end-to-end team preprocessing remain pending.
Public redistribution eligibility for existing gated image samples is unresolved.
