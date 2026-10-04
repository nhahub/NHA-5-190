"""Compare a regenerated manifest with preserved evidence, normalizing line endings."""

from __future__ import annotations

import hashlib

from research_cli import arguments, require_files, run


def main() -> None:
    """Require exact logical content rather than relying on matching row counts."""
    args = arguments("compare_manifest")
    require_files(args.expected, args.generated)
    expected = args.expected.read_bytes().replace(b"\r\n", b"\n")
    generated = args.generated.read_bytes().replace(b"\r\n", b"\n")
    if expected != generated:
        raise ValueError("Regenerated manifest differs; preserve both files for review")
    print("PASS: regenerated manifest exactly matches preserved evidence (LF normalized)")
    print("SHA256:", hashlib.sha256(generated).hexdigest())


if __name__ == "__main__":
    run(main)
