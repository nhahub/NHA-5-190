import json
from pathlib import Path

OUTPUT = Path("configs/m2/model_inference_config_v1.json")

config = {
    "config_version": "1.0.0",
    "status": "protocol_defined_training_blocked",
    "vocabulary_version": "1.0.0",

    "model": {
        "type": "multi_label_baseline",
        "planned_architecture": "independent_per_attribute_logistic_or_linear_heads",
        "training_loss": "masked_binary_cross_entropy",
        "loss_mask": "observation_mask"
    },

    "threshold_selection": {
        "status": "pending_validation_predictions",
        "selection_split": "validation",
        "method": "per_attribute_threshold_search_maximizing_masked_f1",
        "candidate_thresholds": "0.05_to_0.95_step_0.05",
        "minimum_observed_labels_required": "must be declared before threshold fitting",
        "test_isolation": True
    },

    "evaluation": {
        "metric_mask": "observation_mask",
        "missing_labels_in_denominator": False,
        "missing_labels_as_negative": False,
        "metrics": [
            "per_attribute_precision",
            "per_attribute_recall",
            "per_attribute_f1",
            "aggregate_masked_metrics"
        ],
        "support_counts_required": True
    },

    "inference": {
        "score_vector_length": 35,
        "score_range": [0.0, 1.0],
        "ordering": "attribute_vocabulary_v1",
        "support_mask_required": True,
        "observation_mask_required_for_ground_truth_evaluation": True
    },

    "current_blocker": {
        "status": "blocked",
        "reason": "No Fashionpedia training split is available in the current handoff.",
        "training_supported_labels": 0,
        "model_checkpoint": None,
        "validation_thresholds": None
    }
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)

print(f"output = {OUTPUT}")
print(f"config_version = {config['config_version']}")
print(f"training_loss = {config['model']['training_loss']}")
print(f"threshold_method = {config['threshold_selection']['method']}")
print(f"test_isolation = {config['threshold_selection']['test_isolation']}")
print(f"status = {config['status']}")
