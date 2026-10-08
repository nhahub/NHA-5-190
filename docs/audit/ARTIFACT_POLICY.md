# Repository artifact policy

Run with normal Python from the repository root:

```powershell
python scripts/tasks.py artifacts
python scripts/validate_repository.py
python scripts/check_artifacts.py --staged
```

The normal check reads working-tree versions of tracked files and nonignored
untracked files. Ignored local downloads remain local and are not inspected.
The staged check reads exact Git index contents, including force-added ignored
files. The optional pre-commit hook runs the staged check before a commit.
Neither mode audits previous Git history or establishes dataset usage rights.

## Shared checks

- Reject raw/processed data directories, generated artifact directories, and caches.
- Allow only empty `data/raw/.gitkeep` and `data/processed/.gitkeep` placeholders.
- Reject model-weight, private-key, and compiled-bytecode extensions.
- Reject local `.env` files while allowing the documented `.env.example`.
- Reject files over 5 MiB except the exact existing raw and canonical split manifests.
- Recognize private-key markers and GitHub/AWS token patterns; output only file
  paths and violation names, never matched credential values.

`data/manifests/raw_manifest.csv` is an explicit exception protected by the
SHA-256 of its LF-normalized content. This permits Windows CRLF and Git/Linux LF
representations of the same inventory. A future manifest change requires review
and an explicit policy update; it cannot use the exception silently.

`data/manifests/split_manifest.csv` from Omar's merged PR #10 is also protected
by its LF-normalized SHA-256 (`7fecce57a5e61d6e433d9c7c1e1661bed1258b0d7362e833fbd41063a455f93f`).
This narrowly allows the delivered 85,815 assignments (7.88 MB in this Windows
checkout); other large CSVs and changed assignments still fail the check.

The validator still checks record schema and unique IDs independently. Neither
the checksum nor a valid reference establishes that all raw files exist on a
teammate's laptop. Sample inspection does not establish full-dataset validity,
split disjointness, or completed preprocessing.

## Human review remains necessary

Committed Polyvore and Fashionpedia image samples already exist in the baseline.
Their public redistribution eligibility has not been resolved. No sample was
removed, changed, or newly added in this phase. The project owner must decide how
those images may be shared before further publication. Passing artifact checks
does not grant publication rights.

The secret checks cover specific recognizable patterns; they are not a guarantee
that arbitrary passwords or credentials are absent.
