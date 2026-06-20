#!/usr/bin/env python3
"""
Run codex-reference-ci entrypoints using the athena-codex repo .venv.

Examples::

    python scripts/with_athena_venv.py
    python scripts/with_athena_venv.py codex-reference-validate
    python scripts/with_athena_venv.py codex-reference-ci --all
    python scripts/with_athena_venv.py codex-reference-release --tag v0.3.1-holders-1-79.1

Set ``ATHENA_CODEX_ROOT`` to the athena-codex clone, or place it beside this repo as ``../athena-codex``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REFERENCE_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_TOOLS = REFERENCE_ROOT / "deploy" / "tools"

_CLI_MODULES: dict[str, str] = {
    "codex-reference-validate": "codex_reference_ci.validate",
    "codex-reference-build-bundle": "codex_reference_ci.build_bundle",
    "codex-reference-release": "codex_reference_ci.release",
    "codex-reference-ci": "codex_reference_ci.pipeline",
    "codex-reference-run-unit-tests": "codex_reference_ci.unit_tests",
}


def _athena_codex_root() -> Path:
    import os

    raw = (os.environ.get("ATHENA_CODEX_ROOT") or os.environ.get("CODEX_ATHENA_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    sibling = REFERENCE_ROOT.parent / "athena-codex"
    if (sibling / "scripts" / "bootstrap_athena_codex_venv.py").is_file():
        return sibling.resolve()
    raise FileNotFoundError(
        "athena-codex not found. Clone beside codex-atlas-reference or set ATHENA_CODEX_ROOT."
    )


def _venv_python(athena_root: Path) -> Path:
    if sys.platform == "win32":
        return athena_root / ".venv" / "Scripts" / "python.exe"
    return athena_root / ".venv" / "bin" / "python"


def _ensure_venv(athena_root: Path) -> Path:
    py = _venv_python(athena_root)
    if py.is_file():
        return py
    bootstrap = athena_root / "scripts" / "bootstrap_athena_codex_venv.py"
    subprocess.run([sys.executable, str(bootstrap)], cwd=athena_root, check=True)
    if not py.is_file():
        raise FileNotFoundError(f"venv still missing after bootstrap: {py}")
    return py


def _pip_install_editable(py: Path) -> None:
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", "-e", str(DEPLOY_TOOLS)],
        cwd=REFERENCE_ROOT,
        check=True,
    )


def _codex_reference_ci_importable(py: Path) -> bool:
    result = subprocess.run(
        [str(py), "-c", "import codex_reference_ci"],
        cwd=REFERENCE_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _ensure_tools_installed(py: Path, *, reinstall: bool) -> None:
    if reinstall or not _codex_reference_ci_importable(py):
        _pip_install_editable(py)


def _console_script_path(py: Path, name: str) -> Path | None:
    scripts = py.parent
    if sys.platform == "win32":
        candidate = scripts / f"{name}.exe"
    else:
        candidate = scripts / name
    return candidate if candidate.is_file() else None


def _run_command(py: Path, command: str, args: list[str]) -> int:
    module = _CLI_MODULES.get(command)
    if module is not None:
        return subprocess.run([str(py), "-m", module, *args], cwd=REFERENCE_ROOT).returncode
    shim = _console_script_path(py, command)
    if shim is not None:
        return subprocess.run([str(shim), *args], cwd=REFERENCE_ROOT).returncode
    print(f"unknown command: {command}", file=sys.stderr)
    print(f"known: {', '.join(sorted(_CLI_MODULES))}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run codex-reference-ci via athena-codex .venv."
    )
    parser.add_argument(
        "--reinstall-tools",
        action="store_true",
        help="Force editable reinstall of deploy/tools before running the command.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="codex-reference-ci",
        help="CLI name (default: codex-reference-ci)",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the CLI")
    parsed = parser.parse_args(argv)
    cli_args = list(parsed.args)
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]
    athena = _athena_codex_root()
    py = _ensure_venv(athena)
    _ensure_tools_installed(py, reinstall=parsed.reinstall_tools)
    if parsed.command == "codex-reference-ci" and not cli_args:
        cli_args = ["--all"]
    return _run_command(py, parsed.command, cli_args)


if __name__ == "__main__":
    raise SystemExit(main())
