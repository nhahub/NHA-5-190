"""Export the provisional support mask without claiming a trained attribute model."""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/m2"))
from attribute_common import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_VOCABULARY,
    load_vocabulary,
    run,
    safe_output,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR / "attribute_support_v1.csv")
    args = parser.parse_args()
    output = safe_output(args.output, args.vocabulary)
    vocabulary = load_vocabulary(args.vocabulary)
    rows = [
        {
            "vocabulary_version": vocabulary["vocabulary_version"],
            "attribute_index": label["index"],
            "attribute_id": label["attribute_id"],
            "attribute_name": label["name"],
            "support_mask": 0,
            "support_status": "unsupported_pending_training_data",
            "source": "Fashionpedia",
            "evidence_scope": "validation_only",
            "reason": "No Fashionpedia training release/checkpoint is available in this handoff.",
        }
        for label in vocabulary["labels"]
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False, lineterminator="\n")
    print(f"output = {output}")
    print(f"rows = {len(rows)}")
    print("supported = 0")
    print(f"unsupported = {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
