import json
from pathlib import Path

import pandas as pd

TARGETS = Path("data/processed/m2/attribute_targets_validation_sample.csv")
VOCAB = Path("configs/m2/attribute_vocabulary_v1.json")
OUTPUT = Path("reports/m2/sample_prediction_v1.json")

with VOCAB.open("r", encoding="utf-8-sig") as f:
    vocabulary = json.load(f)

targets = pd.read_csv(TARGETS)

row = targets.iloc[0]

observation_mask = json.loads(row["observation_mask"])
vector_length = vocabulary["vector_length"]

sample = {
    "item_id": row["item_id"],
    "scores": None,
    "support_mask": [0] * vector_length,
    "observation_mask": observation_mask,
    "attribute_source": "Fashionpedia",
    "vocabulary_version": vocabulary["vocabulary_version"],
    "model_version": "not_available_training_data_blocked",
    "status": "sample_contract_only",
    "score_semantics": (
        "No model scores are available because the Fashionpedia training split "
        "is missing from the current handoff."
    ),
    "support_mask_semantics": (
        "1 means the attribute is supported for inference by the current model; "
        "0 means unsupported/unavailable."
    ),
    "observation_mask_semantics": (
        "1 means ground-truth attribute evidence is observed for this item; "
        "0 means unknown/unannotated."
    )
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(sample, f, indent=2)

print(f"output = {OUTPUT}")
print(f"item_id = {sample['item_id']}")
print(f"vocabulary_version = {sample['vocabulary_version']}")
print(f"observation_mask_length = {len(observation_mask)}")
print(f"support_mask_length = {len(sample['support_mask'])}")
print(f"scores = {sample['scores']}")
print(f"status = {sample['status']}")
