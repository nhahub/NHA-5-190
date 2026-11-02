"""CLI runner for deterministic candidate generation (Milestone 3).

Usage:
    python scripts/m3/generate_candidates.py \
        --input data/samples/items_representation/examples.json \
        --output artifacts/m3/candidates_sample.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from wardiq.compatibility.candidate_generator import (
    generate_candidates,
    load_candidate_rules,
)


def load_items_from_source(path: Path) -> list[dict[str, Any]]:
    """Load item records from JSON fixtures, JSONL, or CSV manifests."""
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "valid_examples" in data:
                items = []
                for ex in data["valid_examples"]:
                    clean = {k: v for k, v in ex.items() if k != "_comment"}
                    items.append(clean)
                return items
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
            return [data]
        elif isinstance(data, list):
            return data
    elif path.suffix.lower() == ".jsonl":
        items = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items
    elif path.suffix.lower() == ".csv":
        items = []
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                items.append(dict(row))
        return items
    raise ValueError(f"Unsupported input file format: {path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Path to input items")
    parser.add_argument("--output", required=True, type=Path, help="Path to output report JSON")
    parser.add_argument("--rules", type=Path, default=None, help="Path to rules JSON config")
    parser.add_argument("--split", type=str, default=None, help="Target split filter")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for sampling")
    parser.add_argument("--max-candidates", type=int, default=None, help="Max valid candidates")
    parser.add_argument("--max-per-category", type=int, default=None, help="Max per category")
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rules = load_candidate_rules(args.rules)
    raw_records = load_items_from_source(input_path)

    provenance = {
        "code_revision": "v1.0.0",
        "config_ref": str(args.rules or "configs/m3/rules_v1.json"),
        "model_version": "rule_based",
        "cache_version": input_path.name,
    }

    result = generate_candidates(
        raw_records,
        rules=rules,
        target_split=args.split,
        seed=args.seed,
        max_candidates=args.max_candidates,
        max_items_per_category=args.max_per_category,
    )

    report = {
        "schema_version": "wardiq.m3.candidate-report.v1",
        "config_version": result.config_version,
        "input_path": str(input_path),
        "target_split": result.target_split,
        "seed": result.seed,
        "max_candidates": result.max_candidates,
        "max_items_per_category": result.max_items_per_category,
        "input_item_count": result.input_item_count,
        "eligible_item_count": result.eligible_item_count,
        "excluded_item_count": result.excluded_item_count,
        "candidates_emitted": result.candidates_emitted,
        "rejected_combination_count": result.rejected_combination_count,
        "truncated_by_max_candidates": result.truncated_by_max_candidates,
        "eligible_by_category": result.eligible_by_category,
        "item_rejection_counts": result.item_rejection_counts,
        "candidate_rejection_counts": result.candidate_rejection_counts,
        "template_counts": result.template_counts,
        "item_rejections": [
            {
                "item_id": rej.item_id,
                "reasons": list(rej.reasons),
                "common_category": rej.common_category,
                "mapping_status": rej.mapping_status,
                "target_split": rej.target_split,
            }
            for rej in result.item_rejections
        ],
        "valid_candidates": [cand.to_dict(provenance) for cand in result.valid_candidates],
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Generated {result.candidates_emitted} candidates from "
        f"{result.eligible_item_count} eligible items."
    )
    print(f"Report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
