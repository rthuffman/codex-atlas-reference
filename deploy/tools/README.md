# codex-reference-ci

Python CI for **codex-atlas-reference**: validate holder slices, build deterministic release bundles, upload **GitHub Releases**.

Requires **Python 3.14.3** (use the **athena-codex** repo `.venv` — see repo root `README.html`).

## Install (athena-codex venv)

From **codex-atlas-reference** root (sibling `athena-codex` clone recommended):

```bash
python scripts/with_athena_venv.py codex-reference-ci --all
```

Or install explicitly:

```bash
python ../athena-codex/scripts/bootstrap_athena_codex_venv.py
../athena-codex/.venv/bin/python -m pip install -e "./deploy/tools"
```

## CLI

```bash
codex-reference-validate
codex-reference-run-unit-tests
codex-reference-build-bundle
codex-reference-ci --validate --test --build
codex-reference-release --tag v0.3.1-holders-1-79.1
```

Or:

```bash
python -m codex_reference_ci.pipeline --all
```

**Release upload** needs `GITHUB_TOKEN` (or `GH_TOKEN`) and optionally [GitHub CLI](https://cli.github.com/) (`gh`). Set `CODEX_REFERENCE_FORCE_GITHUB_API=1` to skip `gh` and use the REST API.

## Pipeline driver

`codex-reference-ci` is the entry point for local runs and for `.github/workflows/codex-reference-ci.yml`:

| Flag | Action |
|------|--------|
| `--validate` | Check `manifest.json` and pack payloads |
| `--test` | `pytest` under `tests/` |
| `--build` | Write `dist/codex-atlas-reference-<version>.tar.gz` + `.sha256` sidecar |
| `--release TAG` | Build (unless assets exist) and upload to GitHub Releases |

**Suite pin sync:** `codex-reference-release` updates **athena-codex** `codex/docs/atlas_bundles.yaml` and regenerated pin JSON automatically after upload. Opt out with `--no-sync-suite-pin` or `CODEX_REFERENCE_SKIP_SUITE_PIN_SYNC=1`. Local builds can pass `--sync-suite-pin` (add `--dry-run-suite-pin` to validate only). Standalone: `codex-suite-pin-sync` from athena-codex `deploy/tools`.
