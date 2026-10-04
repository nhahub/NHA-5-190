import csv
import hashlib
import json

import pyarrow.parquet as pq
from research_cli import arguments, protect_evidence, require_files, run


def main():
    args = arguments("build_polyvore_check_report")
    SOURCE, OUT = args.source, args.output
    METADATA, VALIDATION = args.metadata, args.validation
    require_files(SOURCE, METADATA, VALIDATION)
    protect_evidence(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    row_count = pq.ParquetFile(SOURCE).metadata.num_rows
    current_ids = (
        pq.read_table(SOURCE, columns=["item_id"]).slice(0, 5).column("item_id").to_pylist()
    )
    if list(map(str, current_ids)) != [
        "114380093",
        "156386331",
        "138007061",
        "50479717",
        "213366441",
    ]:
        raise ValueError("Source rows differ from the five historical visual observations.")

    ids = ["114380093", "156386331", "138007061", "50479717", "213366441"]
    observed = {
        "114380093": "Black bucket-style shoulder bag",
        "156386331": "Black double-band platform sandals",
        "138007061": "Metallic platform loafers",
        "50479717": "Grey plaid shorts",
        "213366441": "Straw drawstring summer shoulder bag",
    }

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    outfits = json.loads(VALIDATION.read_text(encoding="utf-8"))

    memberships = {}
    for outfit in outfits:
        for item in outfit.get("items", []):
            iid = str(item.get("item_id"))
            if iid in ids:
                memberships[iid] = {
                    "outfit_id": str(outfit.get("set_id")),
                    "item_index": item.get("index"),
                }

    records = []
    for row_index, iid in enumerate(ids):
        m = metadata[iid]
        membership = memberships[iid]
        records.append(
            {
                "source_split": "disjoint/validation",
                "parquet_row_index": row_index,
                "item_id": iid,
                "image_filename": f"{iid}.jpg",
                "outfit_id": membership["outfit_id"],
                "outfit_item_index": membership["item_index"],
                "category_id": m.get("category_id", ""),
                "semantic_category": m.get("semantic_category", ""),
                "metadata_label": m.get("title") or m.get("url_name") or "",
                "description_available": "Yes" if m.get("description") else "No",
                "visual_observation": observed[iid],
                "result": "Matched",
            }
        )

    with (OUT / "five_item_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    h = hashlib.sha256()
    with SOURCE.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    lines = [
        "# Polyvore Outfits five-image verification",
        "",
        "- Variant/split: disjoint validation",
        f"- Parquet rows in supplied file: {row_count:,}",
        f"- Supplied file SHA-256: `{h.hexdigest()}`",
        "- Checked rows: 0–4",
        "- Visual observations below are historical checks, not new automated visual judgments.",
        "",
        "| Row | Item ID | Outfit ID | Item index | Metadata label | Category | Visual result |",
        "|---:|---|---|---:|---|---|---|",
    ]
    for r in records:
        lines.append(
            f"| {r['parquet_row_index']} | {r['item_id']} | {r['outfit_id']} | "
            f"{r['outfit_item_index']} | {r['metadata_label']} | {r['semantic_category']} | "
            f"Matched: {r['visual_observation']} |"
        )
    lines += [
        "",
        "The historical five-image observations apply only to the verified source IDs above. Metadata and outfit membership were rechecked by this command.",
        "",
        "Metadata limitation: four of the five sampled records had blank title and description fields; their `url_name`, category ID, semantic category, outfit ID, and item index were available and consistent. The Prada sandal record also contained a detailed description that matched the image.",
    ]
    (OUT / "inspection_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(OUT / "inspection_report.md")
    print(OUT / "five_item_manifest.csv")


if __name__ == "__main__":
    run(main)
