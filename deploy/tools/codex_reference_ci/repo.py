"""Locate codex-atlas-reference repository root."""

from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for _ in range(20):
        if (
            (p / "packs").is_dir()
            and (p / "deploy" / "tools").is_dir()
            and (p / "manifest.json").is_file()
        ):
            return p
        if p.parent == p:
            break
        p = p.parent
    raise FileNotFoundError(
        "Could not find codex-atlas-reference root (expected packs/, manifest.json, deploy/tools). "
        "Run from inside the codex-atlas-reference clone."
    )
