# M1 and M2 merged checkout verification

Date: 2026-10-08. Input checkout: `main` at `65eaa6d`, including Omar's
M1 split PR #10, Eyad's M2 color PR #9 and M1 integration fixes PR #8.
The additional corrections below are local, uncommitted changes.

## Corrections

- Allow the exact delivered split CSV through the 5 MiB artifact check using
  its LF-normalized checksum. Modified assignments and other large files remain
  rejected; the raw and split manifests were not changed.
- Use canonical assignments for generated garments and sample source images.
  Historical garment metadata supplies only the identity bridge. Preserve every
  Polyvore outfit membership, stripping each position suffix separately.
- Add `python scripts/tasks.py splits` to verify inventory coverage, source
  metadata, split methods/seeds, official test isolation, stratification counts
  and image/outfit leakage. Include the command in CI and shared lint scope.
- Generate the missing test-only evaluation inventory under ignored artifacts.
  The file mentioned in Omar's report was not delivered in PR #10; the generated
  file has its own checksum and does not claim identical bytes to that handoff.
  Update the current pipeline instructions and annotate the historical report.

## Verification results

| Check | Result |
|---|---|
| Full pytest suite | 79 passed, 6 subtests passed |
| Lint and formatting | Passed |
| Package type checking | Passed, 12 source files |
| Repository and artifact policy | Passed |
| Documentation links | Passed |
| Script syntax | All entry points parsed successfully |
| Raw/split reconciliation | 85,815 unique IDs, no missing or extra assignments |
| Image/outfit split leakage | 0 conflicts in manifest identities |
| Fashion-MNIST | 54,000 train, 6,000 validation, 10,000 official test |
| Fashionpedia | 1,158 official validation records |
| Polyvore | 14,657 official disjoint validation records |
| Independent seed-42 allocation replay | Exact train/validation set match using sklearn stratified train_test_split on raw manifest order |
| Evaluation export | 10,000 test-only assignments |
| Source image decoding/traceability | All 15 committed samples passed |
| Clean manifest and taxonomy | 85,815 retained records; 0 unmapped observed category IDs |
| Garment preparation | 56 records; 23 usable derivatives, 33 excluded parts/decorations |
| M2 color CLI | 18 successful, 38 excluded, 0 failed |

The color exclusions are the 33 unusable derivatives and 5 Fashion-MNIST
grayscale previews. Tests also iterate through the image and garment loaders,
checking finite RGB tensors and expected shapes, and repeat the color CLI
to compare outputs in the same dependency environment.

The suite emitted one harmless Windows/joblib physical-core detection warning;
tests completed successfully. Checks ran locally with Python 3.13 and the
available dependency toolkit; hosted CI and other Python versions were not run.

## Evidence and limits

Generated evidence is under `artifacts/m1/splits/split_verification.json`,
`artifacts/m1/splits/evaluation_manifest.csv`, `artifacts/m1/quality/`,
`artifacts/m1/garment_manifest.csv`, `artifacts/m1/sample_image_manifest.csv`
and `artifacts/m2/color/v1/`. Reproduce it using
[the current pipeline instructions](../m1/run_pipeline.md).

The canonical split SHA-256 (LF) is
`7fecce57a5e61d6e433d9c7c1e1661bed1258b0d7362e833fbd41063a455f93f`.
The generated evaluation SHA-256 (LF) is
`f83ed0becd393bfdab69fc583bb966d6d407bc6668fd4a75f6c025c66db016f4`.

Full raw datasets and full garment assets remain absent; metadata reconciliation
does not establish full image decoding, full model training or full-dataset color
coverage. Unmasked samples retain background contamination flags and the existing
[visual review limits](../m2/color_sample_review.md). The final M2 feature cache
still requires the other model components and frozen integration contract.
