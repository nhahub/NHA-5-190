"""Small end-to-end example with STUB probabilities (Ziad's real model is not wired in here).

Run: python scripts/ocs_demo.py
"""

import json

from wardiq.compatibility.ocs import load_relevant_pairs, pair_id, recommend

STUB_SCORES = {
    "b1|t1": 0.80,
    "f1|t1": 0.60,
    "b1|f1": 0.70,
    "b2|t2": 0.40,
    "f2|t2": 0.50,
    "b2|f2": 0.60,
}
VERSIONS = {"model": "STUB", "cache": "STUB", "config": "0.1.0"}


def stub_prob(a: str, b: str) -> float:
    return STUB_SCORES[pair_id(a, b)]


outfits_in = {
    "outfit_1": [("t1", "top"), ("b1", "bottom"), ("f1", "footwear")],
    "outfit_2": [("t2", "top"), ("b2", "bottom"), ("f2", "footwear")],
}
pairs = load_relevant_pairs("configs/m3/ocs.json")
candidates = [
    {"outfit_id": name, "items": [{"item_id": i, "category": c} for i, c in items]}
    for name, items in outfits_in.items()
]
cache_ids = {i for items in outfits_in.values() for i, _ in items}
print(json.dumps(recommend(candidates, stub_prob, pairs, VERSIONS, cache_ids, k=2), indent=2))
