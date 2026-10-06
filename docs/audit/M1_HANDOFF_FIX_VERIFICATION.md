# M1 handoff fix verification

Base: remote main `fd635f0`, branch `fix/m1-handoff`, 2026-10-06.
No open PRs were reported before editing. The user pulled the merged archive and
created this branch; no existing teammate implementation or archive was overwritten.

## Fixes

- Integrated Ziad's manifest EDA, reference duplicate checks and sample decoding
  into portable, import-safe commands in the real scripts directory.
- Preserved his original data-quality report with an explicit historical-scope notice.
- Added a deterministic raw-to-clean generator with provenance and cleaning logs.
  The large clean CSV stays ignored under `artifacts/m1/quality/`.
- Added the 46 official Fashionpedia source category names with source-file checksum;
  clean labels resolve by ID while raw source fields and IDs remain preserved.
- Image validation now decodes pixels, rejects corrupt files with nonzero status,
  handles empty inputs, and separates independent source images from preview sheets.
- Added CI generation/reference gates and a separate data-extra source-sample job.

## Verified locally

- 28 tests and six subtests pass, including category alignment, unknown IDs,
  empty-input status, corrupt-record status, and duplicate reference edge cases.
- Two complete generations produced byte-identical clean CSV, JSON report and CSV log.
- All 85,815 items retained, with 1,095 Fashionpedia label-list rows corrected.
- Original source fields remain equal except the intended Fashionpedia label repair.
- Raw manifest bytes and all existing sample evidence remain unchanged.
- Real corrupt JPEG returns exit 1; empty directory returns exit 2 without traceback.
- 15 independent source images decode; manifest reference checks find no duplicate groups.
- Shared lint/format, strict package types, local links, artifact/manifest checks,
  workflow YAML structural checks and `git diff --check` pass.

Clean-manifest SHA-256:
`2a5b15151e7e4115841e7eeb25e53cbc9d85e082f415df081ceb1828ffca93da`.

## Limits

No full raw-image, mask/crop, visual-duplicate or product-level leakage acceptance
is implied. Hana's crops and Hayat's loaders are still separate owner handoffs.
Source ID/name alignment is not approval of an 11-category common taxonomy.
The historical ZIP is preserved; users should use the integrated commands rather
than extract old files over current code. The raw list ordering remains documented
as independent sets; changing the protected raw manifest is outside this fix.

Local checks used Python 3.13.15 and Pillow 12.3.0. Optional EDA used system pandas
3.0.5, outside the declared `<3` data-extra bound; it does not establish a clean
installation against the declared bound. Real CI for this follow-up requires push
and PR validation. No existing dependency range was widened.
