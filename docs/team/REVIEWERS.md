# Review routing and backup decisions

Task ownership remains in [OWNERSHIP.md](OWNERSHIP.md). CODEOWNERS retains the
existing `@nhahub` fallback for GitHub routing; this does not substitute for a
downstream review. No teammate account or backup reviewer has been guessed.

| Boundary | Producer coordination | Downstream reviewers | Backup |
|---|---|---|---|
| M1 data foundation | Eyad with the assigned M1 producers | Ziad and Asmaa | Needs team confirmation |
| M2 representation/cache | Hayat with the assigned M2 producers | Omar, Hana and Asmaa | Needs team confirmation |
| M3 scoring/ranking | Assigned M3 producers | Hana and Asmaa | Needs team confirmation |
| M4 integration/output | Assigned M4 producers with Asmaa | Asmaa and relevant M5 evaluation owners | Needs team confirmation |

The owner must confirm GitHub handles, backup reviewers and Asmaa's canonical
name before replacing fallback CODEOWNERS entries. Confirm each account can access
the repository and accept reviews. No workspace role or repository access setting
is changed by this document.

For a blocked dependency, open the **Handoff blocker** issue template with producer,
consumer, evidence, requested resolution and a verifiable acceptance check. Continue
independent work. Scope changes and fallback dataset choices need the responsible
owner's recorded decision. Close a blocker only when the consumer confirms resolution.

After a downstream review, record the reviewer, commit/artifact version, acceptance
command/result and remaining limits in the PR or issue. Use the
[handoff packet](../HANDOFFS.md); CI success alone is not a domain review.
