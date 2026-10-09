"""Reproduce and verify the provisional attribute handoff without training a model."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from attribute_common import (
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_VOCABULARY,
    ROOT,
    load_vocabulary,
    read_targets,
    resolve_path,
    run,
    safe_output,
    write_json,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output = safe_output(args.output_dir, args.manifest, args.vocabulary)
    manifest, vocabulary = resolve_path(args.manifest), resolve_path(args.vocabulary)
    target = output / "attribute_targets_validation_sample.csv"
    common = ["--manifest", str(manifest), "--vocabulary", str(vocabulary)]
    commands = [
        ["scripts/m2/build_attribute_targets.py", *common, "--output", str(target)],
        ["scripts/m2/validate_attribute_targets.py", *common, "--targets", str(target)],
        [
            "reports/m2/build_supported_attribute_coverage.py",
            *common,
            "--output",
            str(output / "supported_attribute_coverage_v1.csv"),
        ],
        [
            "reports/m2/build_attribute_support.py",
            "--vocabulary",
            str(vocabulary),
            "--output",
            str(output / "attribute_support_v1.csv"),
        ],
        [
            "reports/m2/build_sample_prediction.py",
            *common,
            "--targets",
            str(target),
            "--output",
            str(output / "sample_prediction_v1.json"),
        ],
        [
            "configs/m2/build_model_inference_config.py",
            "--vocabulary",
            str(vocabulary),
            "--output",
            str(output / "model_inference_config_v1.json"),
        ],
    ]
    for command in commands:
        result = subprocess.run(
            [sys.executable, str(ROOT / command[0]), *command[1:]], cwd=ROOT, check=False
        )
        if result.returncode:
            return result.returncode
    targets = read_targets(target)
    vocabulary_config = load_vocabulary(vocabulary)
    sample = json.loads((output / "sample_prediction_v1.json").read_text(encoding="utf-8"))
    if sample["scores"] is not None or any(sample["support_mask"]):
        raise ValueError("The untrained handoff must not claim model scores or inference support")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    paths = [ROOT / command[0] for command in commands] + [
        ROOT / "scripts/m2/attribute_common.py",
        Path(__file__).resolve(),
    ]
    report = {
        "schema_version": "wardiq.attribute-handoff.v1",
        "status": "validation_contract_only_training_blocked",
        "vocabulary_version": vocabulary_config["vocabulary_version"],
        "vector_length": vocabulary_config["vector_length"],
        "source_rows": len(targets),
        "observed_positive_positions": sum(int(value) for value in targets.observed_positive_count),
        "unknown_positions": sum(int(value) for value in targets.unknown_count),
        "known_negative_positions": sum(int(value) for value in targets.negative_count),
        "training_supported_labels": 0,
        "model_checkpoint": None,
        "validation_thresholds": None,
        "code_revision": revision.stdout.strip() if revision.returncode == 0 else "unavailable",
        "source_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "vocabulary_sha256": hashlib.sha256(vocabulary.read_bytes()).hexdigest(),
        "implementation_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
        "output_sha256": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in (
                "attribute_targets_validation_sample.csv",
                "supported_attribute_coverage_v1.csv",
                "attribute_support_v1.csv",
                "sample_prediction_v1.json",
                "model_inference_config_v1.json",
            )
        },
    }
    write_json(output / "attribute_handoff_report.json", report)
    print("Attribute handoff: PASS (validation-only; model training remains blocked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
