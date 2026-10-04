# Phase 3 - existing research portability

## Changes and ownership boundary

- All seven original research scripts now use repository-relative configuration
  and command-line input overrides, with guarded execution on import.
- Existing outputs default to ignored artifacts instead of committed evidence.
- Configuration validation and output protection reject invalid settings and
  accidental writes into preserved manifests/samples/docs/source/configs.
- Added exact normalized manifest comparison, successful run provenance records,
  and a committed-sample decoding/identity check.
- Existing source IDs, row ordering, annotation conventions, and research evidence
  were preserved. No teammate loader, preprocessing, split, crop, taxonomy, model,
  or model evaluation implementation was added.

## Checks performed

- All seven original commands: help, safe import, and local-input execution passed.
- Fashion-MNIST: four gzip checksums verified from existing files; five exports
  reproduce committed preview pixels identically. No fresh download was repeated.
- Fashionpedia: five original image IDs and 46 annotation rows reproduced.
- Polyvore Outfits: five original item IDs and 14,657 parquet rows confirmed;
  metadata and outfit memberships rechecked. Visual judgments remain historical.
- Full raw manifest: 85,815 generated rows exactly match preserved content after
  normalizing CRLF to LF, not merely by comparing counts.
- Sample smoke: 15 files, repeated decode hashes, dimensions, and source IDs pass
  in under one second on this laptop. Fashion-MNIST PNGs are 280x280 previews.
- Missing input produces a concise nonzero failure before output generation.
- Research-run records include their required provenance fields.
- Tests: 14 pass (previously 10); scoped lint, formatting, strict source typing,
  artifact checks, and manifest validation pass.

## Scope limits and human decisions

- This is not the complete M1 preprocessing pipeline or a full-split leakage test.
- Original Polyvore references are outfit-position identities, not product IDs.
  Its 98 FITB index/blank-position differences require dataset-owner interpretation.
- Source records contain canonical raw paths; external CLI overrides do not
  redistribute raw inputs or make those paths exist on teammates' laptops.
- Historical sample-manifest flattened paths are documented rather than rewritten.
- Dataset rights, code licensing, training-annotation verification, and downstream
  handoff review remain pending. New outputs remain ignored and local.
- No random operations exist in these research commands; no unused seed utility
  was introduced. Model experiment infrastructure remains team-owned.
- Normal Pip installation and other Python versions still need clean CI verification.
