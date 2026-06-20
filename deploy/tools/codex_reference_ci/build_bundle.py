"""Build deterministic release bundle (.tar.gz) with SHA256 sidecar."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import tarfile
from pathlib import Path

from codex_reference_ci.manifest import bundle_version, file_sha256, iter_archive_members
from codex_reference_ci.repo import find_repo_root


def _tar_add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    arc = arcname.replace("\\", "/")
    info = tarfile.TarInfo(name=arc)
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def build_bundle(*, repo_root: Path | None = None, output: Path | None = None) -> tuple[Path, Path]:
    root = repo_root or find_repo_root()
    version = bundle_version(root)
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    archive = output or (dist / f"codex-atlas-reference-{version}.tar.gz")

    with archive.open("wb") as raw, gzip.GzipFile(
        fileobj=raw,
        mode="wb",
        filename="",
        mtime=0,
    ) as gz, tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for arcname, src in iter_archive_members(root):
            _tar_add_bytes(tar, arcname, src.read_bytes())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = archive.with_suffix(".tar.gz.sha256")
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, sidecar


def main() -> int:
    parser = argparse.ArgumentParser(description="Build codex-atlas-reference release .tar.gz bundle.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output archive path (default: dist/codex-atlas-reference-<bundle_version>.tar.gz)",
    )
    args = parser.parse_args()
    archive, sidecar = build_bundle(output=args.output)
    print(f"Wrote {archive}")
    print(f"Wrote {sidecar} ({sidecar.read_text(encoding='utf-8').strip()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
