from pathlib import Path
from io import BytesIO

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont


SOURCE = Path(r"C:\Users\Hp\Downloads\0000.parquet")
OUT = Path(r"C:\Users\Hp\Documents\Codex\2026-09-21\n\outputs\polyvore_validation_check")
OUT.mkdir(parents=True, exist_ok=True)

table = pq.read_table(SOURCE, columns=["item_id", "image"]).slice(0, 5)
rows = table.to_pylist()

thumbs = []
for index, row in enumerate(rows):
    item_id = row["item_id"]
    payload = row["image"]
    image = Image.open(BytesIO(payload["bytes"])).convert("RGB")
    path = OUT / f"{index:02d}_{item_id}.jpg"
    image.save(path, quality=95)
    thumb = image.copy()
    thumb.thumbnail((300, 300))
    thumbs.append((item_id, payload.get("path"), image.size, path, thumb))

card_w, card_h = 330, 365
sheet = Image.new("RGB", (card_w * 5, card_h), "white")
draw = ImageDraw.Draw(sheet)
font = ImageFont.load_default()
for i, (item_id, original_path, size, path, thumb) in enumerate(thumbs):
    x = i * card_w + (card_w - thumb.width) // 2
    y = 10 + (300 - thumb.height) // 2
    sheet.paste(thumb, (x, y))
    draw.text((i * card_w + 10, 315), f"Item ID: {item_id}", fill="black", font=font)
    draw.text((i * card_w + 10, 335), f"Source: {original_path}", fill="black", font=font)
    draw.text((i * card_w + 10, 350), f"Size: {size[0]}x{size[1]}", fill="black", font=font)

sheet_path = OUT / "five_item_contact_sheet.jpg"
sheet.save(sheet_path, quality=95)

print(f"ROW_COUNT={pq.ParquetFile(SOURCE).metadata.num_rows}")
for i, (item_id, original_path, size, path, _) in enumerate(thumbs):
    print(f"{i}\t{item_id}\t{original_path}\t{size[0]}x{size[1]}\t{path}")
print(f"CONTACT_SHEET={sheet_path}")
