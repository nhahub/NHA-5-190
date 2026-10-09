> Repository integration update: use [the current portable attribute commands](../../docs/m2/attributes.md). Generated reports/config copies now go to ignored artifacts. This remains a partially complete, untrained handoff.

# M2 Supported Multi-Label Attribute Prediction — Final Handoff

## Overall Status

PARTIALLY COMPLETE — implementation and data-contract requirements are validated. Model training and empirical threshold/metric results are blocked because the current handoff contains no Fashionpedia training split.

## Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | Missing labels do not become negative targets or metric denominators | PASS |
| 2 | Vector length, ordering, and mask semantics match the versioned vocabulary | PASS |
| 3 | Unsupported attributes remain unavailable and provenance is explicit | PASS |
| 4 | Validation support counts and threshold-selection protocol are declared | PARTIAL |
| 5 | Downstream consumers can interpret the prediction contract without guessing | PARTIAL |

### Acceptance 4

Protocol is defined, but actual thresholds and model metrics are blocked by missing training data.

### Acceptance 5

Prediction schema and sample contract are ready, but real model scores are unavailable until a model is trained.

## Validated Results

- Vocabulary version: `1.0.0`

- Vocabulary size: `35`

- Validation annotations: `46`

- Annotations with attributes: `30`

- Empty/unannotated annotations: `16`

- Observed positive positions: `87`

- Unknown/masked positions: `1523`

- Known negatives: `0`

- Target vector length: `35`

- Observation mask length: `35`

- Target/mask consistency errors: `0`

- Consistency status: `PASS`

- Validation-evidence labels: `35/35`

- Training-supported labels: `0`

## Data Blocker

The current raw manifest contains `1158` Fashionpedia rows, all in the `validation` split.

No Fashionpedia training split is available in the current handoff.

Therefore the project must not claim a trained baseline, empirical thresholds, precision, recall, F1, checkpoint, or test performance from the current data.

## Mask Semantics

Observed positive:

`target=1`, `observation_mask=1`

Known negative:

`target=0`, `observation_mask=1`

No explicit known-negative semantics were established in the available handoff.

Unknown/unannotated:

`target=0`, `observation_mask=0`

This is an ignored placeholder and must not contribute to training loss or metric denominators.

## Threshold Protocol

The declared baseline protocol uses masked binary cross-entropy during training.

Per-attribute thresholds are to be selected on validation predictions by maximizing masked F1, with test data isolated until final evaluation.

Actual threshold values are pending training data and model predictions.

## Handoff Artifacts

- `configs/m2/attribute_vocabulary_v1.json`

- `configs/m2/attribute_prediction_schema_v1.json`

- `configs/m2/model_inference_config_v1.json`

- `scripts/m2/build_attribute_targets.py`

- `scripts/m2/validate_attribute_targets.py`

- `data/processed/m2/attribute_targets_validation_sample.csv`

- `reports/m2/supported_attribute_coverage_v1.csv`

- `reports/m2/attribute_support_v1.csv`

- `reports/m2/sample_prediction_v1.json`

- `reports/m2/validation_report_v1.md`

- `reports/m2/M2_handoff_v1.md`

## Reproduction

```powershell

python scripts\\m2\\build_attribute_targets.py

python scripts\\m2\\validate_attribute_targets.py

python reports\\m2\\build_supported_attribute_coverage.py

python reports\\m2\\build_attribute_support.py

python reports\\m2\\build_sample_prediction.py

python configs\\m2\\build_model_inference_config.py
