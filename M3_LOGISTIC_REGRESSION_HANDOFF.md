# WARDIQ M3 — Logistic Regression Handoff

## Model
A Logistic Regression compatibility model using a scikit-learn Pipeline:
StandardScaler + LogisticRegression.

- Feature dimension: 1214
- C: 1.0
- Solver: lbfgs
- Max iterations: 1000
- Positive label: 1
- Selected threshold: 0.316801518201828

## Training
- Training examples: 251,008
- Positive examples: 125,518
- Negative examples: 125,490
- Training split only was used to fit the preprocessing and model.

## Validation
- Validation examples: 67,869
- Positive examples: 33,956
- Negative examples: 33,913
- Threshold selection: Maximum validation F1
- Test data was not used for threshold selection.

| Metric | Value |
|---|---:|
| Accuracy | 0.5470 |
| Precision | 0.5266 |
| Recall | 0.9361 |
| F1 | 0.6740 |
| ROC-AUC | 0.6628 |
| Average Precision | 0.6640 |
| Log Loss | 0.6504 |
| Brier Score | 0.2295 |

## Artifacts
- logistic_regression.joblib
- metrics.json
- validation_predictions.csv
- calibration_report.json

## Calibration
Calibration was assessed using 10 validation reliability bins and the Brier score.
The available evidence does not establish that the predicted probabilities are calibrated.

## Label Limitations
The labels are provisional:
- Positive: source outfit co-occurrence.
- Negative: assumed category-preserving replacement.

The labels do not represent verified human judgments of compatibility.
The model estimates the probability of label 1 under the training examples and sampling process.

## Evaluation Limitations
- Test evaluation was not performed.
- Reload equivalence could not be verified because the original feature matrices were not found.
- Near-duplicate product leakage has not been verified.
- The M2 attribute predictor remains a separate outstanding task.
- The current dataset/model artifacts are provisional and not team-accepted.

## Status
Logistic Regression training and validation artifacts are available.
Further data validation, reload verification, and team acceptance are required before claiming final readiness.
