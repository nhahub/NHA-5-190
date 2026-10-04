# Milestone handoff review

These are documentation requirements for the assigned owners, not implemented
team features. Existing ownership and milestone windows remain unchanged. A date
passing, sample inspection, or infrastructure CI passing does not accept a milestone.
An owner may develop independent components while an upstream contract is pending;
integration and acceptance require the listed upstream artifacts.

## Review packet required from each owner

| Item | Required contents |
|---|---|
| Revision and scope | Git commit, milestone/task, producer, dataset release and source/project splits |
| Reproduction | Exact normal-Python command, required extras and local inputs, configuration, hardware requirements, output locations |
| Schema | Version, row unit, field types/shapes, units and score ranges, missing-value policy, ID/reference rules |
| Artifacts | Inventory, checksums for consumed/generated files, model/cache versions, local acquisition instructions for ignored files |
| Validation | Actual command/output, record counts, failure/exclusion counts, split/leakage scope, metrics with evaluation population |
| Decision and review | Known limits, unresolved choices, downstream reviewer response and remaining blockers |

Generated datasets stay in `data/processed/`; features, models, and reports may use
ignored `artifacts/`. Small schema/configuration documentation can be committed.
Owners choose final filenames and schema versions in their own implementation PRs.
Do not link to a private machine path as the only way to reproduce a result.

Record unavailable annotations as missing, not false negatives. Preserve source
IDs and official split identity in all derived records. Use recorded seeds where
randomness occurs and disclose nondeterministic operations and excluded records.
Each owner's command must reject invalid inputs or document exclusions; downstream
work must not silently treat unresolved references as valid items.

## Acceptance chain

| Handoff | Required upstream result | Downstream reviewers |
|---|---|---|
| M1 to M2 | Inventory, acquired inputs, owner-produced preprocessing/garments/splits/loaders, quality and taxonomy decisions | Ziad and Asmaa; M2 consumers verify their inputs |
| M2 to M3 | Frozen item representation and feature cache, supported categories/attributes/masks/colors/embeddings | Omar, Hana, and Asmaa |
| M3 to M4 | Structurally valid candidates, compatibility scores, OCS, Top-K output and evaluation | Hana and Asmaa |
| M4 to M5 | Versioned personalization/context/WUS outputs and integrated run | Asmaa with each evaluation owner |
| M5 delivery | Reproducible results, limitations, final report/presentation/demo | Project lead/instructor acceptance remains required |

## Needs human

| Decision | Responsible party | Required before |
|---|---|---|
| Code license and rights to redistribute existing source samples | Project/repository owner | Publishing or expanding redistributed data |
| Canonical Asmaa name, teammate GitHub handles, backup reviewers | Project lead/team | Ownership metadata and reviewer routing are finalized |
| Fashionpedia training verification and garment/part taxonomy approval | Dataset owner and project lead with ML team | Training and unified labels are accepted |
| Project split policy and product-level leakage evidence | Omar with downstream reviewers | Compatibility evaluation is accepted |
| Original Polyvore's 98 FITB index/position differences | Dataset owner | Original FITB examples are used for evaluation |
| Exact schemas, embedding shape, score meanings, OCS/WUS formulas, weights and tie rules | Assigned milestone producers and downstream reviewers | Relevant handoff is frozen |
| Metric definitions, baselines and acceptance thresholds | Evaluation owners and project lead | Claims of model quality or completion |
| Real GitHub CI matrix and required merge checks | Repository owner | Infrastructure compatibility and merge protection are confirmed |

No numerical accuracy threshold, recommendation quality target, or WUS weight is
invented here. Owners record approved values in their task PR and handoff packet.
