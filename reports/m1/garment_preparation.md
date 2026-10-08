# M1 Garment Preparation Report — Hana

## Update — split verification against Omar's files (this section added after Omar's train.csv / validation.csv arrived)

Omar delivered `train.csv` (54,000 rows, Fashion-MNIST only) and `validation.csv` (21,815 rows, all three sources). No `test.csv` has been delivered yet. Ran `scripts/verify_split_integrity.py` against `data/manifests/clean_manifest.csv`:

- **0** duplicate `item_id` across the two files.
- **0** Polyvore outfits split across more than one target_split (all 3,000 outfits are wholly inside `validation`; verified by parsing `group_id` as `outfit_id:position` and grouping on the `outfit_id` part — the raw `group_id` string is unique per row and must not be used as the leakage group as-is, see the finding below).
- Fashionpedia and Polyvore are each entirely within `validation` (no train counterpart exists for them at all), so no cross-split leakage is possible for those two sources.
- **10,000 Fashion-MNIST rows (the official `test` source split) are in the clean manifest but in neither split file.** Full result: `reports/m1/split_integrity.md`.

`data/manifests/garment_manifest.csv` now carries `source_target_split` and `leakage_group_id` for every crop, joined from Omar's files. All 56 prototype rows matched (0 unmatched): the 46 Fashionpedia crops/skips → `validation` (group_id = source image id), the 5 Polyvore items → `validation` (group_id = `outfit_id:position`), the 5 Fashion-MNIST items → `train`. This satisfies "keep an explicit mapping from every output to its source item's split" for everything Omar has delivered so far.

**New finding for Omar:** the `group_id` column for Polyvore is formatted `outfit_id:position` (e.g. `223369815:1`), which is unique per row — it matches Ziad's own `outfit_ids` field exactly (checked on all 14,657 rows), but if any downstream code uses this column directly as "the leakage group" it will treat every item as its own group and silently defeat outfit-level leakage protection. The actual outfit id is the part before `:`. Please confirm this is deliberate (i.e. downstream code is expected to split on `:`) or provide a separate outfit-only column.

**Still blocked:** the acceptance item "crop derivatives cannot land in different splits from their source" can only be marked as verified for `train`+`validation`. It is **not yet verified for `test`**, because no test split has been delivered. Do not tick this fully until a test split exists and passes the same check.

---

**Status: prototype only.** Runs on Eyad's five-image samples per source (per the task's "prototype on Eyad's sample as soon as images and annotations are available" instruction). It does **not** cover the full 85,815-row clean manifest — that needs Ziad's usable full images, which are not in this handoff package (see Blockers).

Config: `configs/m1/garment_preparation.yaml` · Script: `scripts/prepare_garment_crops.py` · Manifest produced: `data/manifests/garment_manifest.csv` · Crops: `data/derived/garment_crops/`

Reproduce:
```bash
python scripts/prepare_garment_crops.py
```

## 1. Source geometry formats (inspected)

| Source | Box format | Mask | Notes |
|---|---|---|---|
| Fashionpedia | `bbox_xywh`: `[x, y, w, h]`, absolute pixels, origin top-left, in the source image's own pixel space | `segmentation_present` is a boolean flag only; the actual RLE/polygon coordinates are in the official annotation JSON, not in this manifest | Verified: all 46 sample boxes are within their image bounds, all `w,h > 0` |
| Polyvore Outfits | none | none | Source item photos are already single-garment product images (300×300 in the samples). There is nothing to crop; the image *is* the garment. |
| Fashion-MNIST | none | none | Single centered garment per 28×28 image. Smoke-test scope only (per `taxonomy.json`), not used for garment-specific downstream tasks. |

Crop unit for Fashionpedia is **one crop per annotation**, not per image, since one image can contain several garments. Annotations whose category is a part or decoration (taxonomy `source_role: part`/`decoration`, e.g. pocket, zipper, sleeve, collar) are **not cropped as garments** — they're recorded with `crop_method=skipped_not_a_garment` and kept in the manifest for traceability, per the "not a garment" decision already recorded in `configs/m1/taxonomy.json`.

## 2. Crop policy and coordinate handling

- Boxes are clamped to image bounds before cropping (`clamp_to_image_bounds: true`). None of the 46 sample boxes needed clamping.
- `source_bbox_xywh` (as given by the source) and `processed_bbox_xywh` (as actually applied, after clamping) are both kept in the manifest, so source and processed geometry stay distinguishable, as the task requires.
- No resizing is done in this task. `resize_scale` is recorded as `null` for native-resolution crops, and is **not** null when a step already changed the geometry (see the Fashion-MNIST issue below) — this is exactly the field a later resize step should fill in.

## 3. Fallback policy (deterministic)

Trigger: bbox missing, non-numeric, zero/negative width or height, or fully outside image bounds after clamping → **retain the full image**, flag `fallback_used=true`, record `fallback_reason`.

**Result on the sample:** 0 of the 46 Fashionpedia annotations triggered the fallback — all boxes were valid. So the fallback path is **not exercised by real data yet**. It's validated with a self-test in the script instead (synthetic zero-area, out-of-bounds, and non-numeric boxes), which the script asserts and prints on every run. This should be re-checked against real invalid cases once the full annotation set is available — the 46-sample check is not proof the fallback works at scale, only that the logic is correct on constructed cases.

Polyvore and Fashion-MNIST items are **not** fallback cases in the "missing annotation" sense — they never had geometry to begin with, by design of the source. They're recorded as `full_image_source_precropped` / `full_image_no_geometry` respectively, not as a broken bbox.

## 4. Representative examples

![contact sheet](../../data/derived/garment_crops/contact_sheet.jpg)

| Example | Result | Comment |
|---|---|---|
| `fashionpedia_val_ann_008929` (shoe) | Good | Bbox tightly bounds the shoe. |
| `fashionpedia_val_ann_005699` (jacket) | **Technically valid, visually wrong** | The box is a valid rectangle inside the image, but it also includes the model's head and the shirt underneath — the crop reads as a portrait, not a garment. This is the exact pitfall the task calls out: a valid box is not the same as a usable crop. **Flagged for visual review before this crop is used for anything.** |
| `fashionpedia_val_ann_005700` (watch) | Weak | Box is technically inside bounds but the crop is a few pixels wide and very dark — low visual signal, likely unusable as a training crop even though nothing failed validation. |
| Polyvore item `114380093` | Good, by design | Full source image is already the garment (a bag). |
| Fashion-MNIST `fashion_mnist_train_000000` | Fallback, flagged | Full image kept; see the resolution issue below. |

**Takeaway for the acceptance checklist:** "every crop is usable" cannot be certified from bbox validity alone. The jacket and watch cases pass every geometric check and still need a human visual pass. Recommend a spot-check step (e.g. a contact sheet per batch) before crops go to Hayat, not just an automated bounds check.

## 5. Issues found in the handoff package (not this task's outputs — recording for the owners)

| # | Issue | Where | Owner | Impact on this task |
|---|---|---|---|---|
| 1 | Fashion-MNIST sample manifest references `original_28x28/` and `preview_280x280/` subfolders that don't exist in the package. Only flat 280×280 PNGs are shipped (an upscale of the native 28×28, matching the "2828" note in `reports/m1/data_quality.md`). | `data/manifests/fashion_mnist_sample_manifest.csv` vs `data/samples/fashion_mnist/` | Eyad | Crops in this prototype use the 280×280 file. `resize_scale=0.1` is recorded per row so downstream code can map back to native 28×28. Needs the real 28×28 files before Fashion-MNIST derivatives are trusted at native resolution. |
| 2 | Polyvore sample manifest's `image_filename` (e.g. `114380093.jpg`) doesn't match the shipped file name (`00_114380093.jpg`, prefixed with the row index). | `data/samples/polyvore_outfits/five_item_manifest.csv` vs shipped files | Eyad | Script falls back to a suffix match and logs it; works for this 5-item sample but is not a fix — should not be relied on at full scale. |
| 3 | Fashionpedia `category_ids`/`category_labels` in the manifest are two independently-sorted lists, not positionally paired (already reported by asmaa; unaffected here because this task reads the **per-annotation** sample manifest, which has one `category_id` per row, not the image-level manifest). | `data/manifests/raw_manifest.csv`, `clean_manifest.csv` | Eyad, Ziad | None for this task's crops, but relevant if garment crops are later joined back to the image-level manifest — join by id, not by list position. |

## 6. Limitations

- Prototype scale only: 46 Fashionpedia annotations, 5 Polyvore items, 5 Fashion-MNIST items. The full clean manifest (85,815 rows) has not been run — the raw/full images referenced by `clean_manifest.csv` are not in this handoff package.
- Fashionpedia masks are not used; only bboxes. `segmentation_present` is recorded per row (all `True` in the sample) but the actual polygon/RLE geometry needs the official annotation JSON, which is outside this handoff.
- No attribute/label generation happened, and no custom segmentation model was trained or run, per the task's explicit restriction.
- Split/leakage confirmation with Omar has not happened yet — Omar's split manifests are not delivered (see Blockers). No derivative has been checked against a split boundary.

## 7. Acceptance checklist — status

- [x] Every crop is usable, traceable and linked to its original source item — traceable yes (`source_item_id`, `source_image_path` on every row); "usable" has two visually flagged exceptions (jacket, watch) pending review.
- [x] Bounding box/mask conventions and coordinate transformations are documented (section 1–2).
- [x] Missing-annotation fallback is deterministic and visibly flagged — logic implemented and self-tested; not yet exercised on a real invalid case.
- [~] Crop derivatives cannot land in different splits from their source — **verified for train+validation** (0 leakage, see update above); **not yet verified for test** — Omar has not delivered a test split (10,000 Fashion-MNIST items are unassigned).

## 8. Blockers

| Blocker | Responsible owner | Next action |
|---|---|---|
| Full/raw images for the 85,815-row clean manifest are not in this handoff | Ziad / Eyad | Share the raw image archives or a usable subset so the full run can happen. |
| Test split not yet delivered (10,000 Fashion-MNIST rows unassigned) | Omar | Deliver `test.csv` in the same format as `train.csv`/`validation.csv`; re-run `scripts/verify_split_integrity.py` with all three files. |
| `group_id` format ambiguity for Polyvore (`outfit_id:position`, unique per row) | Omar | Confirm downstream code must split on `:` to get the real leakage group, or provide a dedicated outfit-only column. |
| Native 28×28 Fashion-MNIST files missing | Eyad | Replace or add the `original_28x28/` folder referenced by the sample manifest. |
| Polyvore filename mismatch in the sample manifest | Eyad | Fix `image_filename` values or the shipped file names so they match without a fallback search. |
| Official Fashionpedia annotation JSON (for real mask geometry) | Eyad | Needed if mask-based (not just bbox-based) cropping is required later. |
