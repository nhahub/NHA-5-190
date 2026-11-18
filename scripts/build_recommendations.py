"""Build the M3 -> M4 output: candidates -> pair scores -> mean OCS -> top-K outfits.

pair_scores.json maps "idA|idB" (ids sorted) to a probability. Today it is a stand-in for
Ziad's saved model; swap `prob` below for his model once it is available.

Example:
  python scripts/build_recommendations.py --candidates docs/m3/sample/candidates.json \\
    --cache docs/m3/sample/cache_ids.json --scores docs/m3/sample/pair_scores.json \\
    --model-version STUB --cache-version STUB --out docs/m3/example_output.json
"""

import argparse
import json
from pathlib import Path

from wardiq.compatibility.ocs import ItemUnavailable, load_relevant_pairs, pair_id, recommend

parser = argparse.ArgumentParser()
parser.add_argument("--candidates", required=True)
parser.add_argument("--cache", required=True)
parser.add_argument("--scores", required=True)
parser.add_argument("--config", default="configs/m3/ocs.json")
parser.add_argument("--k", type=int)
parser.add_argument("--model-version", required=True)
parser.add_argument("--cache-version", required=True)
parser.add_argument("--calibration-evidence")
parser.add_argument("--out", required=True)
args = parser.parse_args()

config = json.loads(Path(args.config).read_text(encoding="utf-8"))
candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
cache_ids = set(json.loads(Path(args.cache).read_text(encoding="utf-8")))
scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))


def prob(a: str, b: str) -> float:
    try:
        return float(scores[pair_id(a, b)])
    except KeyError:
        raise ItemUnavailable from None


output = recommend(
    candidates,
    prob,
    load_relevant_pairs(args.config),
    {"model": args.model_version, "cache": args.cache_version, "config": config["config_version"]},
    cache_ids,
    args.k or config["default_k"],
    args.calibration_evidence,
)
Path(args.out).write_text(json.dumps(output, indent=2), encoding="utf-8")
print(f"wrote {args.out}: returned {output['returned_k']}, rejected {len(output['rejected'])}")
