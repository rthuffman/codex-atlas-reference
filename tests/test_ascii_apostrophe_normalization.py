"""Regression: no typographic apostrophes remain in reference packs."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APOS_CHARS = ("\u2018", "\u2019", "\u201B", "\u02BC", "\u00B4", "\u2032")


def test_no_typographic_apostrophes_in_packs() -> None:
    bad = []
    for path in (REPO / "packs").rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        if any(ch in text for ch in APOS_CHARS):
            bad.append(str(path.relative_to(REPO)))
    assert bad == []


def test_mesh_orourke_ascii() -> None:
    import json

    doc = json.loads(
        (REPO / "packs/us_holders_house/people_post_reconstruction_mesh.json").read_text(encoding="utf-8")
    )
    rec = next(r for r in doc["records"] if r.get("ProspectusID") == "72a4cd2a-fa72-774a-a73c-8876756de177")
    assert rec["Name"] == "Beto O'Rourke"
    assert "'" in rec["Name"]
    assert "\u2019" not in rec["Name"]
