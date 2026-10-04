"""CPU smoke check for committed sample decoding and raw-manifest traceability."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Check sample IDs, dimensions, and repeatable decoding without preprocessing."""
    start = time.monotonic()
    files = sorted((ROOT / "data/samples/fashion_mnist").glob("*.png"))
    files += sorted((ROOT / "data/samples/fashionpedia/original").glob("*.jpg"))
    files += sorted((ROOT / "data/samples/polyvore_outfits").glob("[0-9][0-9]_*.jpg"))
    if len(files) != 15:
        raise ValueError(f"Expected 15 baseline source samples; found {len(files)}")
    requested = {}
    for path in files:
        if path.suffix == ".png":
            match = re.match(r"(fashion_mnist_(?:train|test)_\d{6})_", path.stem)
            if not match:
                raise ValueError(f"Unexpected sample filename: {path.name}")
            requested[match.group(1)] = path
        elif path.parent.name == "polyvore_outfits":
            requested["polyvore_outfits_disjoint_validation_" + path.stem.split("_", 1)[1]] = path
        else:
            requested[path.name] = path
    matched = []
    with (ROOT / "data/manifests/raw_manifest.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            path = requested.get(row["item_id"]) or requested.get(row["original_filename"])
            if path is None:
                continue
            hashes = []
            for _ in range(2):
                with Image.open(path) as image:
                    image.load()
                    expected = (int(row["image_width"]), int(row["image_height"]))
                    if row["source_dataset"] == "Fashion-MNIST":
                        config = json.loads((ROOT / "configs/research/m1.json").read_text())
                        scale = config["export_fashion_mnist_samples"]["preview_scale"]
                        expected = (expected[0] * scale, expected[1] * scale)
                    if image.size != expected:
                        raise ValueError(f"Manifest dimensions differ for {path.name}")
                    hashes.append(hashlib.sha256(image.tobytes()).hexdigest())
            if hashes[0] != hashes[1]:
                raise ValueError(f"Repeat decoding differs for {path.name}")
            matched.append({"item_id": row["item_id"], "pixel_sha256": hashes[0]})
    if len(matched) != len(files):
        raise ValueError("Not all samples resolve to raw-manifest records")
    elapsed = time.monotonic() - start
    if elapsed >= 60:
        raise RuntimeError(f"Sample check exceeded CPU budget: {elapsed:.2f}s")
    print(
        json.dumps(
            {"samples": len(matched), "seconds": round(elapsed, 3), "records": matched}, indent=2
        )
    )
    print("PASS: decoding, dimensions, stable IDs, and repeatable pixels; preprocessing not tested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
