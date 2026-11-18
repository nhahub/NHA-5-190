"""Verify Omar's split manifests against Ziad's clean manifest: coverage, duplicate item_ids,
and outfit-level split purity (no Polyvore outfit split across train/validation/test).

This checks the SPLIT FILES THEMSELVES for leakage risk. It is a prerequisite for confirming
that garment-crop derivatives (Hana's task) can safely inherit their source item's split.

Usage (from the repository root):
    python scripts/verify_split_integrity.py --splits data/splits/train.csv data/splits/validation.csv

Exit code is 1 if any check fails (duplicate item_id across files, an outfit split across
more than one target_split, or any clean_manifest item missing a split assignment).
"""
import argparse
import sys
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifests/clean_manifest.csv")
    ap.add_argument("--splits", nargs="+", required=True, help="One or more split CSVs (e.g. train.csv validation.csv). A missing test split is reported, not assumed.")
    ap.add_argument("--out", default="reports/m1/split_integrity.md")
    a = ap.parse_args()

    cm = pd.read_csv(a.manifest, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    parts = [pd.read_csv(p) for p in a.splits]
    splits = pd.concat(parts, ignore_index=True)

    lines = ["# Split integrity check", ""]
    ok = True

    dup = splits.item_id.duplicated()
    lines.append(f"- Duplicate item_id across the given split files: **{int(dup.sum())}**")
    if dup.sum():
        ok = False

    merged = cm.merge(splits[["item_id", "target_split", "group_id"]], on="item_id", how="left")
    cov = merged.groupby(["source_dataset", "target_split"], dropna=False).size()
    lines.append("\n## Coverage (clean_manifest rows x assigned split)\n")
    lines.append("```\n" + cov.to_string() + "\n```")
    missing = merged[merged.target_split.isna()]
    if len(missing):
        ok = False
        by_src = missing.groupby(["source_dataset", "source_split"]).size()
        lines.append(f"\n**Missing split assignment: {len(missing)} rows.**\n```\n{by_src.to_string()}\n```")
        lines.append("These items are in the clean manifest but not in any provided split file "
                      "(e.g. an undelivered test split). They must not be used until Omar assigns them.")

    # Outfit-level leakage check for Polyvore: group_id is "outfit_id:position" (verified
    # identical to Ziad's own outfit_ids field). The real leakage-relevant group is the
    # part before ':'; using the raw group_id as-is would treat every item as its own
    # group and silently defeat this check, so we always split on ':' first.
    pv = merged[merged.source_dataset == "Polyvore Outfits"].copy()
    if len(pv):
        pv["outfit_root"] = pv.group_id.astype(str).str.split(":").str[0]
        per_outfit_splits = pv.groupby("outfit_root").target_split.nunique()
        leaked = per_outfit_splits[per_outfit_splits > 1]
        lines.append(f"\n## Outfit-level split purity (Polyvore)\n")
        lines.append(f"- Distinct outfits: {pv.outfit_root.nunique()}")
        lines.append(f"- Outfits split across more than one target_split: **{len(leaked)}**")
        if len(leaked):
            ok = False
            lines.append(f"  Leaked outfit_root values: {list(leaked.index[:20])}")

    lines.append(f"\n## Result: {'PASS' if ok else 'FAIL'}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
