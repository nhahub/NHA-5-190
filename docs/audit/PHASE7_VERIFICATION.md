# Phase 7 verification

Baseline: `30d001d`, branch `chore/repo-hardening`, 2026-10-04.
The working tree was clean before editing. A live GitHub API lookup confirmed
no open pull requests and only remote `main`.

## Documentation changes

- Repaired all seven broken local link occurrences in dataset decision documents;
  removed their counted exceptions from the CI baseline, which is now empty.
- Replaced temporary ZIP/repository-arrival instructions with existing-clone setup,
  portable raw-input acquisition, real check commands and handoff review steps.
- Added a historical-scope notice to the original Polyvore report. Earlier anonymous
  access failures remain preserved, with links to later approved-access evidence.
  Clarified outfit-position versus product identity and the pending FITB interpretation.
- Added explicit readiness status, inputs, outputs and acceptance evidence to M1-M5.
  Planned dates and passing infrastructure checks do not mark owner tasks complete.
- Added a common review packet, downstream review chain and human decision register.
- Marked architecture/schema examples as draft until producers and reviewers approve.

## Verification

- Local inline Markdown file links pass with zero baseline broken links.
- Repository structure, unchanged 85,815-row manifest and artifact policy pass.
- `git diff --check` passes.
- Owner/deliverable tables remain unchanged, as do code, tests, scripts, source
  configuration, manifests, sample images/reports and historical JSON evidence.
- Original Polyvore's initial observations remain verbatim after the new notice.

Only documentation and the now-empty link exception list changed. Existing
infrastructure tests were not rerun for these documentation-only changes. The
real GitHub CI matrix still requires a pushed run; configuration is not proof of
remote success. No teammate implementation, new assigned deadline, metric target,
approved score formula or acceptance sign-off was invented.

## Needs human

The [handoff decision register](../HANDOFFS.md) records owner/reviewer identities,
licensing/redistribution, taxonomy/training verification, leakage policy, FITB
interpretation, exact schemas/scoring definitions and evaluation targets. Team
owners must provide their own M1-M5 implementations and downstream review evidence.
