# M2 Supported Attribute Prediction - Validation Report

## Status

Target construction and validation are complete for the available Fashionpedia validation sample. Model training is blocked because the current handoff contains no Fashionpedia training split.

## Validation Results

- Vocabulary version: 1.0.0
- Vocabulary size: 35
- Validation annotations: 46
- Annotations with attributes: 30
- Annotations with empty attribute lists: 16
- Observed positive positions: 87
- Unknown/masked positions: 1523
- Known negative positions: 0
- Target vector length: 35
- Observation mask length: 35
- Consistency validation errors: 0
- Consistency status: PASS

## Target and Mask Semantics

Observed positive: target=1, observation_mask=1.
Known negative: target=0, observation_mask=1; no explicit known-negative semantics were established in the available handoff.
Unknown/unannotated: target=0, observation_mask=0. These positions must be ignored by training loss and evaluation metrics and must never be interpreted as known negatives.

## Coverage

All 35 vocabulary labels have observed evidence in the available validation sample. However, training-supported labels: 0, because the available evidence is validation-only.

## Training Data Blocker

The current raw manifest contains 1,158 Fashionpedia rows, all in the validation split. No Fashionpedia training split is available in the current handoff. Therefore no training model, threshold selection, precision, recall, F1, checkpoint, or test performance is claimed.

## Artifacts

- configs/m2/attribute_vocabulary_v1.json
- scripts/m2/build_attribute_targets.py
- scripts/m2/validate_attribute_targets.py
- data/processed/m2/attribute_targets_validation_sample.csv
- reports/m2/supported_attribute_coverage_v1.csv

## Reproduction

python scripts\\m2\\build_attribute_targets.py
python scripts\\m2\\validate_attribute_targets.py
python reports\\m2\\build_supported_attribute_coverage.py
