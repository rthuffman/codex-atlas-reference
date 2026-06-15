#!/usr/bin/env python3
"""Validate a codex-atlas-reference bundle checkout before release packaging."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_PACK_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_REFERENCE_PID_RE = re.compile(r"^72a4cd2a-fa72-774a-a73c-72588[0-9a-f]{7}$", re.I)
_SKELETON_PID_RE = re.compile(r"^72a4cd2a-fa72-774a-a73c-72587[0-9a-f]{7}$", re.I)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _err(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path.as_posix()}: {message}")


def validate_bundle(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return [f"{manifest_path.as_posix()}: missing manifest.json"]
    try:
        manifest = _load_json(manifest_path)
    except Exception as exc:
        return [f"{manifest_path.as_posix()}: invalid JSON: {exc}"]
    if not isinstance(manifest, dict):
        return [f"{manifest_path.as_posix()}: manifest must be an object"]
    if manifest.get("bundle_format_version") != 1:
        _err(errors, manifest_path, "bundle_format_version must be 1")
    bundle_version = str(manifest.get("bundle_version") or "").strip()
    requires_seeds = str(manifest.get("requires_seeds_bundle_version") or "").strip()
    if not bundle_version:
        _err(errors, manifest_path, "bundle_version is required")
    if not requires_seeds:
        _err(errors, manifest_path, "requires_seeds_bundle_version is required")
    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        _err(errors, manifest_path, "packs must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for pack in packs:
        if not isinstance(pack, dict):
            _err(errors, manifest_path, "each pack must be an object")
            continue
        pack_id = str(pack.get("pack_id") or "").strip()
        if not _PACK_ID_RE.match(pack_id):
            _err(errors, manifest_path, f"invalid pack_id {pack_id!r}")
            continue
        files = pack.get("files")
        if not isinstance(files, list) or not files:
            _err(errors, manifest_path, f"{pack_id}: files must be a non-empty list")
            continue
        for file_raw in files:
            rel = str(file_raw or "").strip().replace("\\", "/")
            slice_path = root / "packs" / pack_id / rel
            if not slice_path.is_file():
                _err(errors, slice_path, "slice file missing")
                continue
            try:
                sl = _load_json(slice_path)
            except Exception as exc:
                _err(errors, slice_path, f"invalid JSON: {exc}")
                continue
            if not isinstance(sl, dict):
                _err(errors, slice_path, "slice must be an object")
                continue
            if sl.get("slice_format_version") != 1:
                _err(errors, slice_path, "slice_format_version must be 1")
            if str(sl.get("pack_id") or "") != pack_id:
                _err(errors, slice_path, "pack_id does not match manifest")
            records = sl.get("records")
            if not isinstance(records, list):
                _err(errors, slice_path, "records must be a list")
                continue
            if int(sl.get("record_count") or -1) != len(records):
                _err(errors, slice_path, "record_count does not match records length")
            for idx, row in enumerate(records):
                if not isinstance(row, dict):
                    _err(errors, slice_path, f"records[{idx}] must be an object")
                    continue
                pid = str(row.get("ProspectusID") or "").strip()
                if not _REFERENCE_PID_RE.match(pid):
                    _err(errors, slice_path, f"records[{idx}].ProspectusID must be 72588")
                if pid in seen_ids:
                    _err(errors, slice_path, f"duplicate ProspectusID {pid}")
                seen_ids.add(pid)
                if row.get("VertexType"):
                    if row.get("VertexType") != "Person":
                        _err(errors, slice_path, f"records[{idx}].VertexType must be Person")
                elif row.get("EdgeType"):
                    if row.get("EdgeType") != "HoldsSeat":
                        _err(errors, slice_path, f"records[{idx}].EdgeType must be HoldsSeat")
                    from_pid = str(row.get("from_prospectus_id") or "").strip()
                    to_pid = str(row.get("to_prospectus_id") or "").strip()
                    if not _REFERENCE_PID_RE.match(from_pid):
                        _err(errors, slice_path, f"records[{idx}].from_prospectus_id must be 72588")
                    if not _SKELETON_PID_RE.match(to_pid):
                        _err(errors, slice_path, f"records[{idx}].to_prospectus_id must be 72587")
                else:
                    _err(errors, slice_path, f"records[{idx}] needs VertexType or EdgeType")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate codex-atlas-reference bundle files.")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    errors = validate_bundle(args.root.resolve())
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1
    print("codex-atlas-reference: validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
