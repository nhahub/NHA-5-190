"""Count sample evidence separately from unavailable model training support."""

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/m2"))
from attribute_common import (  # noqa: E402
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_VOCABULARY,
    build_target_and_mask,
    load_vocabulary,
    parse_attribute_ids,
    read_manifest,
    run,
    safe_output,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_DIR / "supported_attribute_coverage_v1.csv"
    )
    args = parser.parse_args()
    output = safe_output(args.output, args.manifest, args.vocabulary)
    vocabulary = load_vocabulary(args.vocabulary)
    source = read_manifest(args.manifest)
    if not source.source_split.eq("validation").all():
        raise ValueError("This coverage report describes validation evidence only")
    ids = [label["attribute_id"] for label in vocabulary["labels"]]
    counts = Counter()
    for value in source.attribute_ids:
        observed = set(parse_attribute_ids(value))
        build_target_and_mask(observed, ids)
        counts.update(observed)
    rows = [
        {
            "vocabulary_version": vocabulary["vocabulary_version"],
            "attribute_index": label["index"],
            "attribute_id": label["attribute_id"],
            "attribute_name": label["name"],
            "observed_positive_count": counts[label["attribute_id"]],
            "support_status": "provisional_validation_only",
            "training_supported": False,
            "source": "Fashionpedia validation sample",
            "source_rows": len(source),
            "reason": "Observed validation evidence does not establish training/model support.",
        }
        for label in vocabulary["labels"]
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False, lineterminator="\n")
    print(f"output = {output}")
    print(f"rows = {len(rows)}")
    print(f"validation_annotations = {len(source)}")
    print(f"labels_with_observed_evidence = {sum(count > 0 for count in counts.values())}")
    print("training_supported_labels = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
