"""Export an explicitly untrained sample contract with null scores."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/m2"))
from attribute_common import (  # noqa: E402
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TARGETS,
    DEFAULT_VOCABULARY,
    load_vocabulary,
    run,
    safe_output,
    validate_targets,
    write_json,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--targets", default=DEFAULT_TARGETS)
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR / "sample_prediction_v1.json")
    args = parser.parse_args()
    output = safe_output(args.output, args.manifest, args.targets, args.vocabulary)
    vocabulary = load_vocabulary(args.vocabulary)
    row = validate_targets(args.manifest, args.targets, vocabulary).iloc[0]
    sample = {
        "item_id": row.item_id,
        "scores": None,
        "support_mask": [0] * vocabulary["vector_length"],
        "observation_mask": json.loads(row.observation_mask),
        "attribute_source": "Fashionpedia",
        "vocabulary_version": vocabulary["vocabulary_version"],
        "model_version": "not_available_training_data_blocked",
        "status": "sample_contract_only",
        "score_semantics": "No trained model/checkpoint is available; no model scores are emitted.",
        "support_mask_semantics": "1 means supported for inference; 0 means unavailable.",
        "observation_mask_semantics": "1 means observed ground truth; 0 means unknown/unannotated.",
    }
    write_json(output, sample)
    print(f"output = {output}")
    print(f"item_id = {sample['item_id']}")
    print("scores = None")
    print("status = sample_contract_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
