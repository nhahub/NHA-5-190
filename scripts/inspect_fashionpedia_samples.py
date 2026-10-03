from pathlib import Path
from collections import defaultdict
import csv
import io
import json
import zipfile

from PIL import Image, ImageDraw, ImageFont

RAW_DIR = Path("data/raw/fashionpedia")
ZIP_PATH = RAW_DIR / "val_test2020.zip"
ANNOTATION_PATH = RAW_DIR / "instances_attributes_val2020.json"

OUTPUT_DIR = Path("data/samples/fashionpedia/validation")
ORIGINAL_DIR = OUTPUT_DIR / "original"
ANNOTATED_DIR = OUTPUT_DIR / "annotated"
SAMPLE_COUNT = 5

COLORS = [
    "#ff3b30",
    "#007aff",
    "#34c759",
    "#ff9500",
    "#af52de",
    "#00c7be",
    "#ff2d55",
]


def safe_name(value):
    return (
        value.replace("/", "-")
        .replace("\\", "-")
        .replace(",", "")
        .replace(" ", "_")
    )


def main():
    if not ZIP_PATH.exists() or not ANNOTATION_PATH.exists():
        raise FileNotFoundError(
            "Fashionpedia validation files are missing. "
            "Download val_test2020.zip and instances_attributes_val2020.json first."
        )

    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

    with ANNOTATION_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    categories = {item["id"]: item["name"] for item in data["categories"]}
    attributes = {item["id"]: item["name"] for item in data["attributes"]}

    annotations_by_image = defaultdict(list)
    for annotation in data["annotations"]:
        annotations_by_image[annotation["image_id"]].append(annotation)

    manifest_rows = []
    report_lines = [
        "# Fashionpedia five-sample validation check",
        "",
        f"- Validation JSON images: {len(data['images'])}",
        f"- Validation annotations: {len(data['annotations'])}",
        f"- Categories: {len(data['categories'])}",
        f"- Attributes: {len(data['attributes'])}",
        "",
    ]
    contact_items = []

    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive_names = set(archive.namelist())
        selected = []

        for image_record in data["images"]:
            archive_name = f"test/{image_record['file_name']}"
            image_annotations = annotations_by_image.get(image_record["id"], [])

            if archive_name in archive_names and image_annotations:
                selected.append((image_record, image_annotations, archive_name))

            if len(selected) == SAMPLE_COUNT:
                break

        if len(selected) < SAMPLE_COUNT:
            raise RuntimeError("Could not find five annotated validation images.")

        for sample_number, (image_record, image_annotations, archive_name) in enumerate(
            selected, start=1
        ):
            image_bytes = archive.read(archive_name)
            original_path = ORIGINAL_DIR / image_record["file_name"]
            original_path.write_bytes(image_bytes)

            with Image.open(io.BytesIO(image_bytes)) as opened:
                image = opened.convert("RGB")

            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()

            segmentation_count = 0
            category_names = []

            for position, annotation in enumerate(image_annotations):
                color = COLORS[position % len(COLORS)]
                x, y, width, height = annotation["bbox"]
                category_name = categories[annotation["category_id"]]
                category_names.append(category_name)

                draw.rectangle(
                    [x, y, x + width, y + height],
                    outline=color,
                    width=max(2, image.width // 350),
                )
                draw.text(
                    (x + 3, max(0, y - 13)),
                    f"{annotation['id']}: {category_name}",
                    fill=color,
                    font=font,
                    stroke_width=1,
                    stroke_fill="white",
                )

                segmentation = annotation.get("segmentation")
                if segmentation:
                    segmentation_count += 1
                    if isinstance(segmentation, list):
                        for polygon in segmentation:
                            if len(polygon) >= 6:
                                points = list(zip(polygon[0::2], polygon[1::2]))
                                draw.line(
                                    points + [points[0]],
                                    fill=color,
                                    width=max(1, image.width // 500),
                                )

                attribute_names = [
                    attributes[attr_id]
                    for attr_id in annotation.get("attribute_ids", [])
                    if attr_id in attributes
                ]

                manifest_rows.append(
                    {
                        "item_id": f"fashionpedia_val_ann_{annotation['id']:06d}",
                        "source_dataset": "Fashionpedia",
                        "source_split": "validation",
                        "source_image_id": image_record["id"],
                        "source_annotation_id": annotation["id"],
                        "image_file_name": image_record["file_name"],
                        "image_path": original_path.as_posix(),
                        "category_id": annotation["category_id"],
                        "category_label": category_name,
                        "attribute_ids": json.dumps(annotation.get("attribute_ids", [])),
                        "attribute_labels": json.dumps(attribute_names, ensure_ascii=False),
                        "bbox_xywh": json.dumps(annotation["bbox"]),
                        "segmentation_present": bool(segmentation),
                    }
                )

            annotated_name = (
                f"sample_{sample_number:02d}_"
                f"image_{image_record['id']}_annotated.jpg"
            )
            annotated_path = ANNOTATED_DIR / annotated_name
            image.save(annotated_path, quality=92)

            summary = (
                f"Sample {sample_number}: image_id={image_record['id']}, "
                f"file={image_record['file_name']}, "
                f"annotations={len(image_annotations)}, "
                f"masks={segmentation_count}, "
                f"categories={'; '.join(sorted(set(category_names)))}"
            )
            print(summary)
            report_lines.append(f"- {summary}")

            preview = image.copy()
            preview.thumbnail((480, 420))
            contact_items.append((preview, f"Sample {sample_number} · image {image_record['id']}"))

    manifest_path = OUTPUT_DIR / "sample_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=manifest_rows[0].keys())
        writer.writeheader()
        writer.writerows(manifest_rows)

    report_path = OUTPUT_DIR / "inspection_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    cell_width = 500
    cell_height = 470
    columns = 2
    rows = (len(contact_items) + columns - 1) // columns
    sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "white")
    sheet_draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, (preview, caption) in enumerate(contact_items):
        column = index % columns
        row = index // columns
        x = column * cell_width + (cell_width - preview.width) // 2
        y = row * cell_height + 30
        sheet.paste(preview, (x, y))
        sheet_draw.text(
            (column * cell_width + 12, row * cell_height + 8),
            caption,
            fill="black",
            font=font,
        )

    contact_sheet_path = OUTPUT_DIR / "five_sample_contact_sheet.jpg"
    sheet.save(contact_sheet_path, quality=92)

    print(f"Manifest: {manifest_path.resolve()}")
    print(f"Report: {report_path.resolve()}")
    print(f"Contact sheet: {contact_sheet_path.resolve()}")


if __name__ == "__main__":
    main()

