# Polyvore Outfits five-image verification

- Variant/split: disjoint validation
- Parquet rows in supplied file: 14,657
- Supplied file SHA-256: `5fdd4413b9fc0fc42d21e2215bdb04a97301b4fc1852b32c155cdeadd98ac331`
- Checked rows: 0–4
- All five embedded JPEG files decoded at 300 × 300 pixels.

| Row | Item ID | Outfit ID | Item index | Metadata label | Category | Visual result |
|---:|---|---|---:|---|---|---|
| 0 | 114380093 | 223369815 | 1 | bucket bag black | bags | Matched: Black bucket-style shoulder bag |
| 1 | 156386331 | 219832237 | 2 | Prada Microsole Leather Double-Band Sandals | shoes | Matched: Black double-band platform sandals |
| 2 | 138007061 | 212053035 | 2 | pierre hardy patent leather platform | shoes | Matched: Metallic platform loafers |
| 3 | 50479717 | 152130081 | 4 | marc jacobs shorts | bottoms | Matched: Grey plaid shorts |
| 4 | 213366441 | 224931182 | 1 | summer lovin shoulder bag | bags | Matched: Straw drawstring summer shoulder bag |

All five images matched their item IDs, available product labels, semantic categories, and disjoint-validation outfit memberships.

Metadata limitation: four of the five sampled records had blank title and description fields; their `url_name`, category ID, semantic category, outfit ID, and item index were available and consistent. The Prada sandal record also contained a detailed description that matched the image.
