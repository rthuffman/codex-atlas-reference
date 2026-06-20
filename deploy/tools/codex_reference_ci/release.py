"""Create or update a GitHub Release and upload bundle assets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests

from codex_reference_ci.build_bundle import build_bundle, bundle_sidecar_path
from codex_reference_ci.manifest import bundle_version, file_sha256
from codex_reference_ci.repo import find_repo_root
from codex_reference_ci.suite_pin_sync import sync_suite_pin as _sync_suite_pin


def _github_repo() -> str:
    return (os.environ.get("GITHUB_REPOSITORY") or "rthuffman/codex-atlas-reference").strip()


def _github_token() -> str:
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN or GH_TOKEN required for release upload")
    return token


def _api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _gh_available() -> bool:
    return subprocess.run(
        ["gh", "--version"],
        capture_output=True,
        text=True,
    ).returncode == 0


def _release_notes(root: Path) -> str:
    manifest = load_bundle_manifest(root)
    notes = str(manifest.get("notes") or "").strip()
    requires_seeds = str(manifest.get("requires_seeds_bundle_version") or "").strip()
    if notes and requires_seeds:
        return f"{notes}\n\nRequires codex-atlas-seeds {requires_seeds}."
    if notes:
        return notes
    if requires_seeds:
        return f"Requires codex-atlas-seeds {requires_seeds}."
    return ""


def upload_with_gh(*, tag: str, archive: Path, sidecar: Path, repo: str, draft: bool, notes: str) -> None:
    title = tag if tag.startswith("v") else f"codex-atlas-reference {tag}"
    create = [
        "gh",
        "release",
        "create",
        tag,
        str(archive),
        str(sidecar),
        "--repo",
        repo,
        "--title",
        title,
    ]
    if notes:
        create.extend(["--notes", notes])
    if draft:
        create.append("--draft")
    print(f"+ {' '.join(create)}", flush=True)
    subprocess.run(create, check=True)


def _get_release_id(repo: str, tag: str, token: str) -> int | None:
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    r = requests.get(url, headers=_api_headers(token), timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    return int(data["id"])


def _create_release(repo: str, tag: str, token: str, *, draft: bool, notes: str) -> int:
    url = f"https://api.github.com/repos/{repo}/releases"
    body: dict[str, Any] = {
        "tag_name": tag,
        "name": tag if tag.startswith("v") else f"codex-atlas-reference {tag}",
        "draft": draft,
        "generate_release_notes": not notes,
    }
    if notes:
        body["body"] = notes
    r = requests.post(url, headers=_api_headers(token), json=body, timeout=60)
    r.raise_for_status()
    return int(r.json()["id"])


def _upload_asset(release_id: int, path: Path, token: str, *, repo: str) -> None:
    upload_url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets"
    params = {"name": path.name}
    headers = _api_headers(token)
    headers["Content-Type"] = "application/octet-stream"
    data = path.read_bytes()
    r = requests.post(upload_url, headers=headers, params=params, data=data, timeout=300)
    r.raise_for_status()


def upload_with_api(*, tag: str, archive: Path, sidecar: Path, repo: str, draft: bool, notes: str) -> None:
    token = _github_token()
    release_id = _get_release_id(repo, tag, token)
    if release_id is None:
        release_id = _create_release(repo, tag, token, draft=draft, notes=notes)
    for path in (archive, sidecar):
        _upload_asset(release_id, path, token, repo=repo)
        print(f"uploaded {path.name} to release {tag}")


def release_bundle(
    *,
    tag: str,
    repo_root: Path | None = None,
    draft: bool = False,
    skip_build: bool = False,
    archive: Path | None = None,
    sync_suite_pin: bool = True,
    dry_run_suite_pin: bool = False,
) -> tuple[Path, Path]:
    root = repo_root or find_repo_root()
    if skip_build and archive is not None:
        arch = archive
        sidecar = bundle_sidecar_path(arch)
    else:
        arch, sidecar = build_bundle(repo_root=root, output=archive)
    repo = _github_repo()
    notes = _release_notes(root)
    if _gh_available() and os.environ.get("CODEX_REFERENCE_FORCE_GITHUB_API") != "1":
        upload_with_gh(tag=tag, archive=arch, sidecar=sidecar, repo=repo, draft=draft, notes=notes)
    else:
        upload_with_api(tag=tag, archive=arch, sidecar=sidecar, repo=repo, draft=draft, notes=notes)
    if sync_suite_pin and os.environ.get("CODEX_REFERENCE_SKIP_SUITE_PIN_SYNC") != "1":
        version = bundle_version(root)
        _sync_suite_pin(
            "reference",
            archive=arch,
            sidecar=sidecar,
            bundle_version_value=version,
            tag=tag,
            dry_run=dry_run_suite_pin,
            repo_root=root,
        )
    manifest = {
        "tag": tag,
        "repository": repo,
        "archive": arch.name,
        "archive_sha256": file_sha256(arch),
        "sidecar": sidecar.name,
    }
    out = root / "dist" / "release-manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return arch, sidecar


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and upload codex-atlas-reference bundle to GitHub Releases.")
    parser.add_argument("--tag", required=True, help="Git tag / release tag (e.g. v0.3.1-holders-1-79.1)")
    parser.add_argument("--draft", action="store_true", help="Create draft release")
    parser.add_argument("--skip-build", action="store_true", help="Upload existing dist archive")
    parser.add_argument("--archive", type=Path, default=None, help="Archive path when --skip-build")
    parser.add_argument(
        "--no-sync-suite-pin",
        action="store_true",
        help="Do not update athena-codex codex/docs/atlas_bundles.yaml and generated pins",
    )
    parser.add_argument(
        "--dry-run-suite-pin",
        action="store_true",
        help="Validate suite pin sync without writing athena-codex files",
    )
    args = parser.parse_args()
    try:
        release_bundle(
            tag=args.tag,
            draft=args.draft,
            skip_build=args.skip_build,
            archive=args.archive,
            sync_suite_pin=not args.no_sync_suite_pin,
            dry_run_suite_pin=args.dry_run_suite_pin,
        )
    except (RuntimeError, subprocess.CalledProcessError, requests.HTTPError) as exc:
        print(f"release failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
