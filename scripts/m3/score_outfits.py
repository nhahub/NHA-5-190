"""CLI runner for scoring outfit candidates and computing OCS (Milestone 3).

Usage:
    python scripts/m3/score_outfits.py --candidates artifacts/m3/polyvore_candidates_report.json --output artifacts/m3/scored_outfits.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wardiq.compatibility.scoring import score_outfit_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path, help="Path to candidates report JSON")
    parser.add_argument("--output", required=True, type=Path, help="Path to output scored outfits JSON")
    args = parser.parse_args()

    candidates_path = args.candidates.resolve()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    valid_candidates = data.get("valid_candidates", [])

    scored_outfits = []
    for cand in valid_candidates:
        item_ids = cand["item_ids"]
        # Dummy mock embeddings for demonstration / runner execution
        mock_embeddings = {iid: [0.1] * 512 for iid in item_ids}
        result = score_outfit_candidate(item_ids, mock_embeddings)
        
        scored = dict(cand)
        scored["pairwise_scores"] = [dict(ps) for ps in result.pairwise_scores]
        scored["ocs"] = result.ocs
        scored_outfits.append(scored)

    # Sort candidates by OCS descending
    scored_outfits.sort(key=lambda x: x.get("ocs") if x.get("ocs") is not None else -1.0, reverse=True)
    for rank, outfit in enumerate(scored_outfits, start=1):
        outfit["rank"] = rank

    report = {
        "schema_version": "wardiq.m3.scored-outfits-report.v1",
        "input_candidates": str(candidates_path),
        "total_scored": len(scored_outfits),
        "ranked_outfits": scored_outfits,
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Successfully scored and ranked {len(scored_outfits)} outfit candidates.")
    print(f"Report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())