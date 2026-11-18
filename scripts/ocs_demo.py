"""Small end-to-end example with STUB probabilities (Ziad's real model is not wired in here).

Run: python scripts/ocs_demo.py
"""

import json

from wardiq.compatibility.ocs import build_m3_output, load_relevant_pairs, pair_id, score_outfit

STUB_SCORES = {"b1|t1": 0.80, "f1|t1": 0.60, "b1|f1": 0.70, "b2|t2": 0.40, "f2|t2": 0.50, "b2|f2": 0.60}
VERSIONS = {"model": "STUB", "cache": "STUB", "config": "0.1.0"}


def stub_prob(a: str, b: str) -> float:
    return STUB_SCORES[pair_id(a, b)]


outfits_in = {
    "outfit_1": [("t1", "top"), ("b1", "bottom"), ("f1", "footwear")],
    "outfit_2": [("t2", "top"), ("b2", "bottom"), ("f2", "footwear")],
}
pairs = load_relevant_pairs("configs/m3/ocs.json")
scored = [
    score_outfit(name, [{"item_id": i, "category": c} for i, c in items], stub_prob, pairs, VERSIONS)
    for name, items in outfits_in.items()
]
print(json.dumps(build_m3_output(scored, k=2, versions=VERSIONS), indent=2))
