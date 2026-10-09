# Provisional supported-attribute handoff

Ziad's `dabb8a7` handoff supplies target construction, observation masks, a
35-label vocabulary and an untrained prediction contract. It does not supply a
trained attribute model, checkpoint, fitted thresholds or empirical model metrics.
The available Fashionpedia inventory contains validation records only.

## Reproduce

Install `.[data]`, then run this portable command from the repository root:

```powershell
python scripts/tasks.py attributes
```

It builds and validates targets, exports coverage/support reports, writes a
sample prediction contract and copies the declared model protocol. The command
stops on any failed stage. Outputs are ignored under `artifacts/m2/attributes/v1/`:

- `attribute_targets_validation_sample.csv`
- `supported_attribute_coverage_v1.csv`
- `attribute_support_v1.csv`
- `sample_prediction_v1.json`
- `model_inference_config_v1.json`
- `attribute_handoff_report.json`, including source/vocabulary/implementation
  checksums and output checksums

All entry points resolve default paths against the repository, support explicit
input/output arguments and have import-safe main guards. Direct target building
still defaults to the ignored legacy `data/processed/m2/` path. The combined
command passes its artifact path explicitly. Report/config generators now default
to artifacts and refuse to overwrite committed manifests, samples, configuration,
source files or report evidence.

For example, to validate a generated target file separately:

```powershell
python scripts/m2/validate_attribute_targets.py --targets artifacts/m2/attributes/v1/attribute_targets_validation_sample.csv
```

## Meaning of the arrays

Vocabulary indices are contiguous and follow ascending source attribute IDs.
Each vector has 35 positions. IDs and names match the delivered annotation sample;
this is a provisional subset, not the full Fashionpedia vocabulary.

- Observed positive: `attribute_target=1`, `observation_mask=1`.
- Unknown/unannotated: stored target placeholder `0`, `observation_mask=0`.
  These positions are excluded from loss and metric denominators.
- Known negatives: none are established by this handoff. Attribute absence must
  not be treated as an observed negative.
- Inference support: `support_mask` is distinct from observation. All positions
  remain `0` because no trained model/checkpoint is supplied. `scores` is `null`,
  explicitly permitted by the provisional schema, rather than fabricated scores.

The sample contains 46 annotation IDs, 35 observed vocabulary labels, 87 positive
positions and 1,523 unknown positions. No known-negative or trained-support claim
is made. Some annotations describe parts/decorations; target construction covers
the complete annotation sample, not just the usable garment crops.

The validator rejects ID coverage/duplicates, wrong vocabulary versions,
source dataset/split changes, malformed or short vectors, nonbinary entries,
incorrect masks/targets and inconsistent summary counts with a nonzero exit code.
The original validator printed `FAIL` with exit code zero; that behavior is fixed.
The sample pipeline is now exercised by the source-sample CI job and regression
tests, including repeatable exports and unchanged committed report evidence.

## Remaining work

Obtain and verify the Fashionpedia training release and training-label support
before fitting a baseline. Resolve supervision/known-negative semantics, freeze
the supported vocabulary with Hanaa, fit thresholds on validation predictions and
report support-aware metrics. The committed model configuration is a protocol
declaration; its planned loss and threshold search are not implementations.
The final M2 representation/cache still requires the remaining selected models
and Hanaa's frozen contract. The original handoff summaries are under
`reports/m2/`; use the commands here for current reproduction.
