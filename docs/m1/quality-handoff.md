# Runnable M1 quality handoff

This follow-up integrates the useful checks from Ziad's merged PR #2 archive into
normal repository paths. Existing research scripts, raw manifests and source
samples are preserved. The archived ZIP remains unchanged; do not extract it over
the current repository. This does not implement Hana's crops or Hayat's loaders.

## Run from the repository root

```powershell
python -m pip install -e ".[dev,data]"
python scripts/tasks.py clean-manifest
python scripts/tasks.py duplicates
python scripts/tasks.py m1-images
python scripts/tasks.py m1-eda
```

`clean-manifest` and `duplicates` use only the standard library and existing
package code. `m1-images` needs Pillow; EDA needs pandas. All input/output paths
can be overridden with the scripts' `--help` options. Inputs supplied on the CLI
resolve from the calling directory; default paths resolve from the repository root.

## Generated outputs

| File under `artifacts/m1/quality/` | Meaning |
|---|---|
| `clean_manifest.csv` | Raw image inventory plus manifest-only statuses and source-ID-resolved Fashionpedia label lists |
| `cleaning_report.json` | Counts, scope, raw/mapping/output SHA-256 values and changed-label count |
| `cleaning_log.csv` | Schema/ID and mapping checks, with image/geometry checks explicitly NOT_RUN |
| `duplicate_groups.csv` | Duplicate item IDs, rows, source identities or references; not visual duplicate detection |
| `sample_image_validation.csv` | Decode results for independent source samples, excluding contact sheets/annotated previews |

The large clean CSV is generated locally and ignored by Git. Consumers use this
documented path or pass an explicit path to their loaders. No new large-file
exception is introduced. Sharing the generated file requires an approved channel
and agreement on the relevant dataset metadata terms.

## Category correction

The preserved raw manifest's Fashionpedia category ID and label lists were sorted
independently. They must not be paired by position. The clean generator resolves
each source category ID using `configs/m1/fashionpedia_categories.json`, which
contains the 46 source names from the already inspected official validation JSON.
It records the source file checksum and [official download source](https://github.com/cvdfoundation/fashionpedia#download).
This is a source-ID lookup, not approval of a cross-dataset taxonomy.

Unknown/empty IDs stop generation before outputs are written; no labels are guessed.
All original fields except the corrected Fashionpedia `category_labels` are kept.
Raw IDs, row ordering and source membership are preserved. `category_label_resolution`
records how labels were handled. No raw image availability is assumed.

To check deterministic regeneration, run the generator twice with the same raw
manifest and mapping into different output directories. Compare the generated
clean-manifest SHA-256 and report contents. Source-byte checksums reflect input
line endings; normalized clean CSV output uses LF and UTF-8 without a BOM.

## Validation behavior and limits

The image command verifies file structure and decodes pixels. Exit 0 means all
found source samples passed, 1 means a validation/dependency/output error, and 2
means no source samples were found. A successful sample check does not establish
full-dataset image availability, correct labels, garment geometry or split leakage.
Fashion-MNIST samples are enlarged grayscale previews, not suitable for garment-color
evaluation. The existing `samples` command separately checks IDs and dimensions.

Duplicate checks return nonzero when duplicate memberships exist. Empty optional
identity fields do not group unrelated records. Grouping an identical reference
across splits can expose reference reuse, but does not prove product/visual leakage
freedom when different references point to the same product or content.

The [original quality report](ziad-quality-report-original.md) is retained as
historical evidence, not a replacement for the current commands or new validation.
Full raw images, garment preparation, loaders and downstream M1 acceptance remain
the responsible owners' handoffs.
