# Split integrity check

- Duplicate item_id across the given split files: **0**

## Coverage (clean_manifest rows x assigned split)

```
source_dataset    target_split
Fashion-MNIST     train           54000
                  validation       6000
                  NaN             10000
Fashionpedia      validation       1158
Polyvore Outfits  validation      14657
```

**Missing split assignment: 10000 rows.**
```
source_dataset  source_split
Fashion-MNIST   test            10000
```
These items are in the clean manifest but not in any provided split file (e.g. an undelivered test split). They must not be used until Omar assigns them.

## Outfit-level split purity (Polyvore)

- Distinct outfits: 3000
- Outfits split across more than one target_split: **0**

## Result: FAIL