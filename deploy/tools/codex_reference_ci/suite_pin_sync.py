"""Invoke athena-codex suite pin sync after bundle build/release."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Literal

from codex_reference_ci.athena_venv import ensure_athena_venv
from codex_reference_ci.manifest import bundle_version
from codex_reference_ci.repo import find_repo_root

BundleKind = Literal["seeds", "reference"]


def _athena_codex_root() -> Path:
    from codex_reference_ci.athena_venv import athena_codex_root

    return athena_codex_root()


def _ensure_codex_ci_installed(python: Path) -> None:
    athena_root = _athena_codex_root()
    deploy_tools = athena_root / "deploy" / "tools"
    subprocess.run(
        [str(python), "-m", "pip", "install", "-q", "-e", str(deploy_tools)],
        check=True,
    )


def sync_suite_pin(
    kind: BundleKind,
    *,
    archive: Path,
    sidecar: Path,
    bundle_version_value: str | None = None,
    tag: str | None = None,
    dry_run: bool = False,
    repo_root: Path | None = None,
) -> None:
    root = repo_root or find_repo_root()
    version = str(bundle_version_value or bundle_version(root)).strip()
    python = ensure_athena_venv()
    _ensure_codex_ci_installed(python)
    cmd = [
        str(python),
        "-m",
        "codex_ci.atlas_bundle_pin_sync",
        "--kind",
        kind,
        "--archive",
        str(archive.resolve()),
        "--sidecar",
        str(sidecar.resolve()),
        "--bundle-version",
        version,
    ]
    if tag:
        cmd.extend(["--tag", tag])
    if dry_run:
        cmd.append("--dry-run")
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    print("Use codex-reference-release or codex-reference-build-bundle --sync-suite-pin", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
