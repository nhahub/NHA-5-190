"""Integration checks against PairFeatureBuilder output."""

import json
from pathlib import Path

import numpy as np

from wardiq.compatibility.pair_features import PairFeatureBuilder, make_config
from wardiq.compatibility.rule_baseline import PairScore, score_pair_features


def _item(item_id: str, axis: int, category: str = "top") -> dict:
    vector = np.eye(1, 512, axis, dtype=np.float32).ravel().tolist()
    return {
        "schema_version": "1.0.0",
        "item_id": item_id,
        "category": {
            "common_category": category,
            "mapping_status": "direct",
            "category_schema_version": "1.0.0",
        },
        "embedding": {
            "model": "openai/clip-vit-base-patch32",
            "model_version": "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268",
            "dimension": 512,
            "vector": vector,
        },
        "attributes": {"scores": None, "mask": None},
        "color": {"model": None, "model_version": None, "palette": None},
        "split": {"target_split": "train"},
    }


def test_rule_baseline_accepts_shared_pair_feature_output() -> None:
    config = make_config(["jeans"])
    builder = PairFeatureBuilder(config, "train")
    builder.add_item(_item("top-a", 0))
    builder.add_item(_item("top-b", 1, "bottom"))
    vector = builder.transform_pair("top-a", "top-b")
    reverse_vector = builder.transform_pair("top-b", "top-a")
    assert np.array_equal(vector, reverse_vector)

    result = score_pair_features(
        feature_names=config["feature_names"], feature_values=vector.tolist()
    )
    reverse_result = score_pair_features(
        feature_names=config["feature_names"], feature_values=reverse_vector.tolist()
    )

    assert result == reverse_result
    assert isinstance(result, PairScore)
    assert result.status == "scored"
    assert result.signals_used == ("embedding", "category")


def test_config_builds_with_real_35_attribute_vocabulary() -> None:
    config_path = Path("configs/m3/pair_features_v1.json")
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    config = make_config(saved_config["attributes"])

    assert len(saved_config["attributes"]) == 35
    assert config["feature_names"] == saved_config["feature_names"]
    assert config["dimension"] == saved_config["dimension"]
