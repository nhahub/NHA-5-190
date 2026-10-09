"""Export the committed attribute protocol to an ignored directory."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/m2"))
from attribute_common import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_VOCABULARY,
    ROOT,
    load_vocabulary,
    resolve_path,
    run,
    safe_output,
    write_json,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=ROOT / "configs/m2/model_inference_config_v1.json")
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR / "model_inference_config_v1.json")
    args = parser.parse_args()
    output = safe_output(args.output, args.source, args.vocabulary)
    config = json.loads(resolve_path(args.source).read_text(encoding="utf-8-sig"))
    if config.get("status") != "protocol_defined_training_blocked":
        raise ValueError("Expected the provisional training-blocked protocol")
    vocabulary = load_vocabulary(args.vocabulary)
    if (
        config["vocabulary_version"] != vocabulary["vocabulary_version"]
        or config["inference"]["score_vector_length"] != vocabulary["vector_length"]
    ):
        raise ValueError("Protocol and vocabulary versions/vector lengths must agree")
    write_json(output, config)
    print(f"output = {output}")
    print(f"config_version = {config['config_version']}")
    print(f"status = {config['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
