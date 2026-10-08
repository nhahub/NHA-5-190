"""Apply configs/m1/taxonomy.json to the M1 manifest and check that every observed label is covered.

Usage (from the repository root):
    python scripts/apply_taxonomy.py
    python scripts/apply_taxonomy.py --manifest data/manifests/raw_manifest.csv

Import `load_taxonomy` and `map_category` in loaders to attach common categories to records.
Exit code is 1 if any observed source label is missing from the taxonomy.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DATASET_KEYS = {
    "Fashion-MNIST": "fashion_mnist",
    "Fashionpedia": "fashionpedia",
    "Polyvore Outfits": "polyvore_outfits",
}


def load_taxonomy(path=ROOT / "configs/m1/taxonomy.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index(tax):
    idx = {}
    for key, src in tax["sources"].items():
        if key == "polyvore_outfits":
            by_label = {e["source_label"]: e for e in src["category_map"]}
            idx[key] = {
                int(i): by_label.get(lbl) for i, lbl in src["source_id_to_semantic"].items()
            }
        else:
            idx[key] = {e["source_id"]: e for e in src["category_map"]}
    return idx


def map_category(tax, dataset_key, source_category_id):
    """Return a source-ID mapping, or None for an unavailable category."""
    if "_idx" not in tax:
        tax["_idx"] = _index(tax)
    try:
        return tax["_idx"].get(dataset_key, {}).get(int(source_category_id))
    except (TypeError, ValueError, OverflowError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", default=str(ROOT / "configs/m1/taxonomy.json"))
    ap.add_argument("--manifest", default=str(ROOT / "artifacts/m1/quality/clean_manifest.csv"))
    ap.add_argument("--out", default=str(ROOT / "artifacts/m1/taxonomy_coverage.csv"))
    ap.add_argument(
        "--mapped-out", help="Optional enriched manifest; source fields remain unchanged"
    )
    a = ap.parse_args()

    outputs = [Path(a.out)] + ([Path(a.mapped_out)] if a.mapped_out else [])
    protected = {Path(a.manifest).resolve(), Path(a.taxonomy).resolve()}
    if any(path.resolve() in protected for path in outputs):
        raise ValueError("Outputs must not overwrite source inputs")
    if len({path.resolve() for path in outputs}) != len(outputs):
        raise ValueError("Coverage and mapped manifest require different output paths")
    tax = load_taxonomy(a.taxonomy)
    df = pd.read_csv(a.manifest, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if "cleaning_status" in df.columns:
        df = df[df.cleaning_status == "retained"]

    rows, missing = [], []
    for name, g in df.groupby("source_dataset"):
        key = DATASET_KEYS.get(name)
        if key is None:
            missing.append((name, "unsupported_dataset"))
            continue
        counts = Counter(int(i) for x in g.category_ids for i in x.split(";") if i)
        for cid, n in sorted(counts.items()):
            m = map_category(tax, key, cid)
            if m is None:
                missing.append((key, cid))
                continue
            rows.append(
                {
                    "source_dataset": name,
                    "source_category_id": cid,
                    "source_label": m["source_label"],
                    "records_with_category": n,
                    "common_category": m["common_category"],
                    "mapping_status": m["mapping_status"],
                }
            )
        if (
            key == "fashionpedia"
        ):  # labels must be looked up by id: manifest label order does not follow id order
            names = {e["source_id"]: e["source_label"] for e in tax["sources"][key]["category_map"]}
            bad = sum(
                1
                for ids, lb in zip(g.category_ids, g.category_labels)
                if {names.get(int(i), f"unknown:{i}") for i in ids.split(";") if i}
                != set(lb.split(";"))
            )
            print(
                "Fashionpedia images whose id-derived label set differs "
                f"from manifest labels: {bad}"
            )

    out = pd.DataFrame(
        rows,
        columns=[
            "source_dataset",
            "source_category_id",
            "source_label",
            "records_with_category",
            "common_category",
            "mapping_status",
        ],
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False)
    print(out.groupby(["source_dataset", "mapping_status"]).size().to_string())
    print(f"Observed source category ids missing from taxonomy: {len(missing)} {missing[:10]}")
    print(f"Coverage written to {a.out}")
    if a.mapped_out:
        if Path(a.mapped_out).resolve() == Path(a.manifest).resolve():
            raise ValueError("Mapped output must not overwrite the source manifest")
        enriched = df.copy()
        mappings = [
            [
                map_category(tax, DATASET_KEYS.get(row.source_dataset), cid)
                for cid in row.category_ids.split(";")
                if cid
            ]
            for row in df.itertuples()
        ]
        enriched["common_categories"] = [
            ";".join(sorted({m["common_category"] for m in entries if m and m["common_category"]}))
            for entries in mappings
        ]
        enriched["direct_common_categories"] = [
            ";".join(
                sorted(
                    {
                        m["common_category"]
                        for m in entries
                        if m and m["common_category"] and m["mapping_status"] == "direct"
                    }
                )
            )
            for entries in mappings
        ]
        Path(a.mapped_out).parent.mkdir(parents=True, exist_ok=True)
        enriched.to_csv(a.mapped_out, index=False)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"Taxonomy application failed: {error}", file=sys.stderr)
        raise SystemExit(1)
