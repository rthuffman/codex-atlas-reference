"""Regression: name/sticker pollution cleaned in reference people packs."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RESIDUAL = re.compile(
    r"(?i)^\s*-\s+|\((?:R|D|DR|FL|Prog|Proh|Soc|Ind)| from |changed to |,\s*$"
)
ROLE_STICKER = re.compile(
    r"(?i)\b(representing|represents the|occupied the chair|labor-member|management-member)\b"
    r"|^\s*Chair\s*\("
)

EXPECT = {
    "72a4cd2a-fa72-774a-a73c-88a96ed06a5d": ("Nelson Dingley Jr.", "Dingley"),
    "72a4cd2a-fa72-774a-a73c-889446680430": ("George Hearst", "Hearst"),
    "72a4cd2a-fa72-774a-a73c-88973ac135e2": ("Henry A. du Pont", "du Pont"),
    "72a4cd2a-fa72-774a-a73c-88ec7ee3ede2": ("Kenneth D. McKellar", "McKellar"),
    "72a4cd2a-fa72-774a-a73c-8808ad8d8987": ("Claude L'Engle", "L'Engle"),
    "72a4cd2a-fa72-774a-a73c-8821e260a7b7": ("Pierce Butler", "Butler"),
    "72a4cd2a-fa72-774a-a73c-882265d1b41d": ("Richard F. Pettigrew", "Pettigrew"),
    "72a4cd2a-fa72-774a-a73c-88809ad26b01": ("Harold Hagen", "Hagen"),
}


def _people() -> list[dict]:
    out: list[dict] = []
    for path in (REPO / "packs").rglob("people*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for rec in doc.get("records") or []:
            if isinstance(rec, dict) and rec.get("VertexType") == "Person":
                out.append(rec)
    return out


def test_known_pollution_pids_cleaned() -> None:
    by_pid = {r["ProspectusID"]: r for r in _people() if r.get("ProspectusID") in EXPECT}
    for pid, (name, family) in EXPECT.items():
        rec = by_pid[pid]
        assert rec["Name"] == name, pid
        assert rec["Sticker"] in (name, "Associate Justice"), pid  # Butler may appear as role elsewhere
        if rec["Sticker"] == name:
            assert rec["FamilyName"] == family, pid
        assert "'" not in (rec.get("FamilyName") or "") or "\u2019" not in json.dumps(rec)


def test_no_party_date_pollution_in_display_fields() -> None:
    bad = []
    for rec in _people():
        name = str(rec.get("Name") or "")
        sticker = str(rec.get("Sticker") or "")
        family = str(rec.get("FamilyName") or "")
        raw = str((rec.get("Sidecar") or {}).get("raw") or "")
        if RESIDUAL.search(name) or RESIDUAL.search(family) or (raw and RESIDUAL.search(raw)):
            bad.append(rec.get("ProspectusID"))
            continue
        if RESIDUAL.search(sticker) and not ROLE_STICKER.search(sticker):
            bad.append(rec.get("ProspectusID"))
    assert bad == []


def test_lengle_ascii_apostrophe_and_parts() -> None:
    pid = "72a4cd2a-fa72-774a-a73c-8808ad8d8987"
    rec = next(r for r in _people() if r.get("ProspectusID") == pid)
    assert rec["Name"] == "Claude L'Engle"
    assert rec["FamilyName"] == "L'Engle"
    assert rec["GivenName"] == "Claude"
    assert "\u2019" not in rec["Name"] + rec["FamilyName"]
