# WARDIQ M1 — Taxonomy Finalization Decisions (v1.0.0)

Made by: asmaa farahat (task owner) · Date: 2026-09-27
Basis: downstream work is already building on the draft taxonomy, so the task owner decided the 6 flagged
categories directly instead of waiting on a separate Project Lead approval round. These are the task owner's
calls, not a recorded team or lead vote. This file is the
record of what was decided and why, so it can be revisited if a lead disagrees later — nothing here
is silently guessed, every call has a stated reason.

The general "no cross-dataset mapping in M1" caveat still applies to the vocabulary as a whole; this
only resolves the 6 items that were sitting as `ambiguous`/`unmapped`.

| Category | Was | Now | Common category | Reasoning |
|---|---|---|---|---|
| **cardigan** | ambiguous (top / outerwear) | resolved | `top` | Grouped with its closest sibling, `sweater` (id 2, direct → top). A cardigan is a knit top worn open — it's not a weatherproofing/structural layer the way a jacket or coat is, so `top` fits its actual function better than `outerwear`. |
| **vest** | ambiguous (outerwear / top) | resolved | `outerwear` | Kept as outerwear. A vest is sleeveless and worn *over* a top as a layering piece (padded vest, suit vest, puffer vest) — same functional role as jacket/coat, which are both `direct → outerwear`. |
| **watch** | ambiguous (accessory_other / jewellery) | resolved | `jewellery` | Moved from `accessory_other` to `jewellery`. For outfit-compatibility scoring, a watch behaves like other body-worn jewellery (bracelet-adjacent) more than like a functional accessory such as a belt or glove. Revisit if Polyvore's own fine-grained watch category (still not in the handoff — see open finding #2) turns out to sit elsewhere. |
| **leg warmer** | unmapped | resolved | `accessory_other` | No legwear/hosiery bucket exists in the 11-category vocabulary. Mapped to the same catch-all used for belt/tie/glove/umbrella rather than forcing a false match to `bottom` or `footwear`. |
| **tights, stockings** | unmapped | resolved | `accessory_other` | Same reasoning as leg warmer. |
| **sock** | unmapped | resolved | `accessory_other` | Worn on the foot but is not footwear itself (not a shoe); no hosiery bucket exists, so it goes to `accessory_other` for the same reason as leg warmer and tights. |

## What this changes

- `configs/m1/taxonomy.json` → version bumped `0.1.0 → 1.0.0`, status `early_handoff_proposed → finalized_by_task_owner_pending_lead_review`. The "resolve ambiguous mappings" item is removed from `open_decisions`; the cross-dataset-approval and Polyvore-names items remain open (separate from this).
- `reports/m1/taxonomy_coverage.csv` → the 6 rows above now show their final `common_category` and `mapping_status` (`approximate`, not `ambiguous`/`unmapped`).
- Fashionpedia mapping summary is now: **15 direct, 12 approximate, 0 ambiguous, 0 unmapped, 19 not_a_garment** (was 15 / 6 / 3 / 3 / 19).

## Still genuinely open (not decided here)

- Whether cross-dataset mapping is allowed in M1 at all (the vocabulary itself is still a proposal per the original handoff rule).
- Polyvore's own fine-grained category names and the full Fashionpedia attribute list (294) — needed to double-check the `watch → jewellery` call once available.

If a lead reviews this later and disagrees with any of the 6 calls above, only `taxonomy.json`
needs a version bump (`1.0.1`) and a re-run of `apply_taxonomy.py` — nothing downstream needs to be
re-derived by hand, since everything reads the category map by id.
