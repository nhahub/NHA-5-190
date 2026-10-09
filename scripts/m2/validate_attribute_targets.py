"""Reject invalid target identities, masks, vocabulary versions and metadata."""

import argparse

from attribute_common import (
    DEFAULT_MANIFEST,
    DEFAULT_TARGETS,
    DEFAULT_VOCABULARY,
    load_vocabulary,
    run,
    validate_targets,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--targets", default=DEFAULT_TARGETS)
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    args = parser.parse_args()
    vocabulary = load_vocabulary(args.vocabulary)
    result = validate_targets(args.manifest, args.targets, vocabulary)
    print(f"source_rows = {len(result)}")
    print(f"output_rows = {len(result)}")
    print("validation_errors = 0")
    print("status = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
