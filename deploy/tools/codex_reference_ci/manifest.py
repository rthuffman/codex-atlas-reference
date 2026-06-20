"""Load and enumerate codex-atlas-reference bundle manifests."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def load_bundle_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing manifest.json at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest.json must be a JSON object")
    return data


def bundle_version(root: Path) -> str:
    version = str(load_bundle_manifest(root).get("bundle_version") or "").strip()
    if not version:
        raise ValueError("manifest.json bundle_version is required")
    return version


def iter_archive_members(root: Path) -> list[tuple[str, Path]]:
    """Return deterministic (arcname, source_path) pairs for release tarballs."""
    manifest = load_bundle_manifest(root)
    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        raise ValueError("manifest.packs must be a non-empty list")

    members: list[tuple[str, Path]] = [("manifest.json", root / "manifest.json")]
    for pack in sorted(packs, key=lambda row: str((row or {}).get("pack_id") or "")):
        if not isinstance(pack, dict):
            raise ValueError("manifest.packs entries must be objects")
        pack_id = str(pack.get("pack_id") or "").strip()
        files = pack.get("files")
        if not pack_id or not isinstance(files, list) or not files:
            raise ValueError(f"manifest pack {pack_id!r} must declare files")
        for file_raw in sorted(str(item or "").strip().replace("\\", "/") for item in files):
            src = root / "packs" / pack_id / file_raw
            if not src.is_file():
                raise FileNotFoundError(f"missing slice file: {src}")
            members.append((f"packs/{pack_id}/{file_raw}", src))
    return members


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_repo(root: Path) -> list[str]:
    tools = root / "tools"
    tools_str = str(tools)
    if tools_str not in sys.path:
        sys.path.insert(0, tools_str)
    from validate_reference_bundle import validate_bundle

    return validate_bundle(root)
