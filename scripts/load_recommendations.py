"""Load an M3 -> M4 output file, check it against the contract and print the ranking.

Run: python scripts/load_recommendations.py docs/m3/example_output.json
"""

import json
import sys
from pathlib import Path

from wardiq.compatibility.ocs import validate_output

output = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
problems = validate_output(output)
if problems:
    print("INVALID:", *problems, sep="\n  - ")
    sys.exit(1)

print(f"valid (contract {output['contract_version']}, versions {output['versions']})")
for row in output["top_k"]:
    print(f"  #{row['rank']} {row['outfit_id']}  ocs={row['ocs']:.3f}  pairs={len(row['pairs'])}")
for row in output["rejected"]:
    print(f"  rejected {row['outfit_id']}: {row['reason']}")
