> Repository update (2026-10-08): this historical verification describes external
> integrated handoff artifacts, including files absent from this checkout. It does
> not certify the newly merged repository implementation. See
> [the repository integration verification](../audit/M1_MERGE_INTEGRATION_VERIFICATION.md)
> for reproducible checks of the current code and remaining data limitations.

# WARDIQ M1 — Final Verification Report

Owner: asmaa farahat · Task: Taxonomy, M1 documentation & verification
Verification date: 2026-09-27 · Basis: Hayat's integrated pipeline (HANDOFF_STATUS.md, loader_checks.md,
run_pipeline.md), cross-checked independently against the delivered manifests where the raw files were
available in the team's temporary handoff packages.

**Verdict: PASS with recorded scope limitations — ready for Project Lead review, not yet a full-scale M1 sign-off.**
See §3 before treating this as unconditional.

---

## 1. Checklist required by this task (Phase 5)

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Stable IDs | **PASS** | `integrated_m1_manifest.csv`: 85,815 rows, 85,815 unique `item_id`, 0 duplicates. Independently recomputed, matches Hayat's and Ziad's figures. |
| 2 | Source traceability | **PASS** | Every row keeps `source_dataset`, `source_image_id`, `original_image_reference`/`annotation_reference`, `source_category_ids_list`. Confirmed present on all 85,815 rows (no blank `item_id`/`source_dataset`). |
| 3 | Valid paths | **PARTIAL — scope-limited** | Garment derivative paths: 0 missing on the 56 prototype rows (independently verified). Image-level paths: cannot be filesystem-verified at full scale — the raw image archives for the 85,815 records are not included in the temporary handoff (confirmed absent in this export). This matches Ziad's §7 finding and is not a new problem; it's a standing blocker, not a defect. |
| 4 | Mapped labels | **PASS** | `apply_taxonomy.py` re-run on `taxonomy_coverage.csv`: every observed source category id across all 3 datasets resolves to a taxonomy entry (0 missing). The 6 categories that were `ambiguous`/`unmapped` (cardigan, vest, watch, leg warmer, tights/stockings, sock) have been **decided by the task owner** (2026-09-27, `taxonomy_decisions.md`; not yet reviewed by the Project Lead) rather than left pending — 0 ambiguous, 0 unmapped remain. The broader "is the 11-category vocabulary approved for cross-dataset use at all" question is unaffected by this and stays open. |
| 5 | Explicit missingness | **PASS** | Missing-value policy (`null` + `<field>_status`, `unavailable_in_source` vs `not_annotated`) is documented and applied consistently; spot-checked against Fashionpedia attribute coverage (59.89% annotation-level, explicitly reported, not defaulted to negative). No fabricated values found. |
| 6 | Available geometry | **PASS, self-tested only** | Fashionpedia `bbox_xywh` documented, clamped to bounds, 0/46 sample boxes needed clamping. Fallback logic (missing/zero/out-of-bounds → full image) is implemented and covered by synthetic self-tests, but **not yet exercised on a real invalid box** — real data hasn't produced one yet. Flag this as "logic verified, real-world trigger unverified," not as a gap in the logic itself. |
| 7 | Split membership | **PASS (resolved)** | `integrated_m1_manifest.csv`: 0 rows with missing `target_split`; counts reconcile exactly to Fashion-MNIST 54,000/6,000/10,000 (train/val/test), Fashionpedia 1,158 validation, Polyvore 14,657 validation — independently recomputed and matches Hayat's report. **Note:** an earlier check (Hana's `split_integrity.md`) recorded this as FAIL because Omar's `test.csv` hadn't been delivered yet at that point. That gap has since closed — kept in §3 as a timeline note, not a current defect. **Update (2026-09-27):** Omar's original split artifacts (`split_manifest.csv`, `train.csv`, `validation.csv`, `test.csv`, `evaluation_manifest.csv`, `split_checks.md`) were received and independently re-verified directly — figures match exactly what was already confirmed via Hayat's integration. Minor formatting note: `test.csv` contains one blank leading row (10,001 raw lines vs. 10,000 real items); not a data defect. Omar's files are no longer an open item. |
| 8 | Leakage evidence | **PASS** | 0 duplicate `item_id` across splits. Polyvore: 3,000 outfits, 0 outfits split across more than one `target_split` (grouping correctly done on the `outfit_id` part of `group_id`, not the raw string — see §3 item 4). |
| 9 | Crop/split consistency | **PASS** | Independently compared `target_split` vs `source_target_split` on all 56 garment rows: **0 mismatches**. Every derivative inherits its source item's split. (This satisfies Omar's task acceptance item "every crop derivative inherits its original source split," which is still unticked on his task page — documentation lag, not a technical failure; see §3 item 5.) |
| 10 | Loader counts | **PASS** | Image-level: 85,815/85,815 rows loadable by split. Garment-level: 56 rows total, 23 usable derivatives (13 Fashionpedia crops, 5 Polyvore full-image, 5 Fashion-MNIST full-image fallback), 33 correctly excluded (`skipped_not_a_garment`). Matches Hayat's and Hana's figures exactly. |
| 11 | M1→M2 contract fields | **PASS (code-verified)** | Inspected `src/wardiq_m1/datasets.py` directly: both dataset classes return all 8 required keys — `item_id`, `source_dataset`, `image_path`, `category_label`, `available_attributes`, `bounding_box`, `segmentation_mask`, `split` — with unavailable values as explicit `None`, not omitted. Hayat's reported "3/3 regression tests passed" was **not re-executed in this session** (no test environment available here) — treat as owner-reported, not independently reproduced. |

---

## 2. Independent spot-checks performed (beyond re-reading owner reports)

- Recomputed row/unique-ID counts on `integrated_m1_manifest.csv` and `garment_integrated_m1_manifest.csv` directly with pandas — all figures matched the owners' write-ups exactly.
- Recomputed the `target_split` vs `source_target_split` comparison on garment rows myself (not just read Hana's claim) — 0 mismatches confirmed.
- Visually inspected the garment-crop contact sheet: confirms the shoe crop is clean, the jacket crop does include the head/torso as Hana flagged, the watch crop is a thin dark sliver as Hana flagged, and the Fashion-MNIST/Polyvore fallbacks are full images as expected. Hana's visual-review flags are real, not overstated.
- Re-read `apply_taxonomy.py` and confirmed it looks up Fashionpedia labels **by category id**, not by manifest row position — the fix for the id/label mismatch bug is real in the code path that matters (taxonomy application and the loaders), even though the underlying raw manifest still carries the original mismatched columns.

## 3. Open items — record before this task is marked Completed

1. **Full raw images not in the handoff.** The 85,815-record image-level manifest is complete and internally consistent, but no full-scale image decode/path validation has happened yet, by anyone. This is the single largest reason M1 cannot be called fully verified at scale.
2. **Garment derivatives are prototype-scale (56 rows, 23 usable).** Not the full dataset. Needs Hana to re-run once full images are available.
3. **Polyvore `group_id` format ambiguity**, flagged by Hana: it's `outfit_id:position` (unique per row). Leakage checks here correctly split on `:`, but any future code that treats `group_id` as the leakage group as-is will silently break outfit-level leakage protection. Needs Omar to confirm this is deliberate or add a dedicated outfit-id column.
4. **Two acceptance checkboxes on Omar's task page are unticked** ("join Hana's derivative mapping," "every crop derivative inherits its source split") even though the task is marked Completed and the underlying check now passes (see item 9 above). Recommend Omar update his page to match reality.
5. **Two garment crops need a human visual pass before use**, even though they passed every automated geometry check: the jacket crop (includes head/torso) and the watch crop (near-zero visual signal).
6. **Taxonomy category resolution done; vocabulary-level approval still open.** The 6 previously ambiguous/unmapped categories are finalized (see `taxonomy_decisions.md`) and no longer block anyone. Whether the 11-category common vocabulary is approved for cross-dataset use in general is a separate, still-open question per the original "no cross-dataset mapping in M1" rule.
7. **Fashionpedia `category_ids`/`category_labels` positional mismatch** (found by asmaa) is still present in the raw/clean manifest itself. Downstream code now correctly reads by id, so it's not propagating — but Eyad/Ziad should still fix or annotate the source manifest so future contributors don't re-introduce the bug.

## 4. Recommendation

Move this task from **In Progress → In Review**, not Completed. The taxonomy, integration, and split/leakage/contract checks all pass on the data that exists today — including Omar's own split files, now independently verified — and the 6 previously-ambiguous categories have been finalized directly rather than left blocking (see item 6 and `taxonomy_decisions.md`). The remaining items (full raw images not yet available, prototype-scale garments, and whether the vocabulary as a whole is approved for cross-dataset use) are genuine and outside this task's ability to close alone. Route items 3, 4 and 7 above to their owners; keep this report as the evidence trail for the milestone review.
