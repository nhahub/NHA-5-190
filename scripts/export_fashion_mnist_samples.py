import csv
import struct
import zlib

from research_cli import ROOT, arguments, protect_evidence, run

DATA_DIR = ROOT / "data/raw/fashion_mnist"
OUTPUT_DIR = ROOT / "artifacts/m1/fashion_mnist"
ORIGINAL_DIR = OUTPUT_DIR / "original_28x28"
PREVIEW_DIR = OUTPUT_DIR / "preview_280x280"

IMAGE_FILE = DATA_DIR / "train-images-idx3-ubyte"
LABEL_FILE = DATA_DIR / "train-labels-idx1-ubyte"

CLASSES = [
    "T-shirt_top",
    "Trouser",
    "Pullover",
    "Dress",
    "Coat",
    "Sandal",
    "Shirt",
    "Sneaker",
    "Bag",
    "Ankle_boot",
]

NUMBER_OF_SAMPLES = 5
PREVIEW_SCALE = 10


def png_chunk(chunk_type, data):
    body = chunk_type + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def write_grayscale_png(path, width, height, pixels):
    rows = bytearray()
    for row in range(height):
        rows.append(0)
        start = row * width
        rows.extend(pixels[start : start + width])

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(
        png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0),
        )
    )
    png.extend(png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9)))
    png.extend(png_chunk(b"IEND", b""))
    path.write_bytes(png)


def enlarge_pixels(pixels, width, height, scale):
    enlarged = bytearray()
    for row in range(height):
        source_row = pixels[row * width : (row + 1) * width]
        wide_row = bytearray()
        for pixel in source_row:
            wide_row.extend([pixel] * scale)
        for _ in range(scale):
            enlarged.extend(wide_row)
    return enlarged


def load_samples():
    with IMAGE_FILE.open("rb") as image_file:
        image_magic, image_count, rows, columns = struct.unpack(">IIII", image_file.read(16))
        if image_magic != 2051:
            raise ValueError("Invalid IDX image file.")
        images = [image_file.read(rows * columns) for _ in range(NUMBER_OF_SAMPLES)]

    with LABEL_FILE.open("rb") as label_file:
        label_magic, label_count = struct.unpack(">II", label_file.read(8))
        if label_magic != 2049:
            raise ValueError("Invalid IDX label file.")
        labels = list(label_file.read(NUMBER_OF_SAMPLES))

    if image_count != label_count:
        raise ValueError("Image and label counts do not match.")

    if NUMBER_OF_SAMPLES > image_count or len(labels) != NUMBER_OF_SAMPLES:
        raise ValueError("Requested samples exceed available IDX records.")
    if any(len(image) != rows * columns for image in images):
        raise ValueError("Truncated IDX image record.")
    if any(label >= len(CLASSES) for label in labels):
        raise ValueError("Invalid Fashion-MNIST label.")
    return images, labels, rows, columns, image_count


def main():
    global DATA_DIR, OUTPUT_DIR, ORIGINAL_DIR, PREVIEW_DIR, IMAGE_FILE, LABEL_FILE
    global NUMBER_OF_SAMPLES, PREVIEW_SCALE
    args = arguments("export_fashion_mnist_samples")
    DATA_DIR, OUTPUT_DIR = args.data_dir, args.output
    NUMBER_OF_SAMPLES, PREVIEW_SCALE = args.count, args.preview_scale
    ORIGINAL_DIR, PREVIEW_DIR = OUTPUT_DIR / "original_28x28", OUTPUT_DIR / "preview_280x280"
    IMAGE_FILE, LABEL_FILE = (
        DATA_DIR / "train-images-idx3-ubyte",
        DATA_DIR / "train-labels-idx1-ubyte",
    )
    protect_evidence(OUTPUT_DIR)
    if not IMAGE_FILE.exists() or not LABEL_FILE.exists():
        raise FileNotFoundError(
            "Fashion-MNIST IDX files were not found. Run download_fashion_mnist.py first."
        )

    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    images, labels, rows, columns, total = load_samples()
    manifest_rows = []

    for index, (pixels, label_number) in enumerate(zip(images, labels)):
        class_name = CLASSES[label_number]
        item_id = f"fashion_mnist_train_{index:06d}"
        filename = f"{item_id}_{class_name}.png"

        original_path = ORIGINAL_DIR / filename
        preview_path = PREVIEW_DIR / filename

        write_grayscale_png(original_path, columns, rows, pixels)

        enlarged = enlarge_pixels(pixels, columns, rows, PREVIEW_SCALE)
        write_grayscale_png(
            preview_path,
            columns * PREVIEW_SCALE,
            rows * PREVIEW_SCALE,
            enlarged,
        )

        manifest_rows.append(
            {
                "item_id": item_id,
                "source_dataset": "Fashion-MNIST",
                "source_split": "train",
                "source_index": index,
                "category_label": class_name.replace("_", " "),
                "original_image_path": original_path.as_posix(),
                "preview_image_path": preview_path.as_posix(),
            }
        )

        print(f"Saved index {index}: label {label_number} ({class_name.replace('_', ' ')})")

    manifest_path = OUTPUT_DIR / "sample_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=manifest_rows[0].keys())
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"\nVerified dataset count: {total}")
    print(f"Original PNGs: {ORIGINAL_DIR.resolve()}")
    print(f"Enlarged previews: {PREVIEW_DIR.resolve()}")
    print(f"Sample manifest: {manifest_path.resolve()}")


if __name__ == "__main__":
    run(main)
