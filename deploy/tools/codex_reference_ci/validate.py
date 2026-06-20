"""Validate bundle checkout."""

from __future__ import annotations

import argparse
import sys

from codex_reference_ci.manifest import validate_repo
from codex_reference_ci.repo import find_repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate codex-atlas-reference manifest and pack payloads.")
    parser.parse_args()
    root = find_repo_root()
    errors = validate_repo(root)
    if errors:
        for msg in errors:
            print(f"error: {msg}", file=sys.stderr)
        print(f"validation failed ({len(errors)} issue(s))", file=sys.stderr)
        return 1
    print(f"ok: {root} manifest and packs valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
