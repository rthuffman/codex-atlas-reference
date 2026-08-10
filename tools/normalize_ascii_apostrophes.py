"""Normalize typographic apostrophe-like chars to ASCII U+0027 in reference packs."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Map lookalike apostrophes / curly singles to ASCII apostrophe.
APOS_CHARS = ("\u2018", "\u2019", "\u201B", "\u02BC", "\u00B4", "\u2032")
APOS_TABLE = str.maketrans({ch: "'" for ch in APOS_CHARS})


def normalize_text(value: str) -> str:
    return value.translate(APOS_TABLE)


def normalize_obj(obj):
    changed = 0
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nv, n = normalize_obj(v)
            out[k] = nv
            changed += n
        return out, changed
    if isinstance(obj, list):
        out = []
        for v in obj:
            nv, n = normalize_obj(v)
            out.append(nv)
            changed += n
        return out, changed
    if isinstance(obj, str):
        nv = normalize_text(obj)
        return nv, (0 if nv == obj else 1)
    return obj, 0


def main() -> None:
    touched = []
    for path in sorted((REPO / "packs").rglob("*.json")):
        raw = path.read_text(encoding="utf-8")
        if not any(ch in raw for ch in APOS_CHARS):
            continue
        data = json.loads(raw)
        new_data, n = normalize_obj(data)
        if n == 0:
            continue
        if isinstance(new_data, dict):
            new_data["reference_bundle_version"] = "0.4.8-ascii-apostrophe"
        path.write_text(json.dumps(new_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        touched.append({"file": str(path.relative_to(REPO)).replace("\\", "/"), "string_fields_changed": n})
    print(json.dumps(touched, indent=2))
    # residual scan
    residual = []
    for path in (REPO / "packs").rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        if any(ch in text for ch in APOS_CHARS):
            residual.append(str(path))
    print("residual_files", residual)


if __name__ == "__main__":
    main()
