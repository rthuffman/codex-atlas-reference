"""Regression: SCOTUS vs Senate Pierce Butler identity split; FJC brackets expanded."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SENATOR_PID = "72a4cd2a-fa72-774a-a73c-8821e260a7b7"
SCOTUS_PID = "72a4cd2a-fa72-774a-a73c-887e2186c5af"
EDGE_PID = "72a4cd2a-fa72-774a-a73c-888f3c06751f"


def test_pierce_butler_identities_split() -> None:
    senate = json.loads(
        (REPO / "packs/us_holders_senate/people_pre_civil_war.json").read_text(encoding="utf-8")
    )
    senator = next(r for r in senate["records"] if r.get("ProspectusID") == SENATOR_PID)
    assert senator["Name"] == "Pierce Butler"
    assert senator["Sticker"] == "Pierce Butler"
    assert (senator.get("Sidecar") or {}).get("bioguide_id") == "B001186"

    appointed = json.loads(
        (REPO / "packs/usg_appointed_holders/people_appointed_c.json").read_text(encoding="utf-8")
    )
    scotus = next(r for r in appointed["records"] if r.get("ProspectusID") == SCOTUS_PID)
    assert scotus["Name"] == "Pierce Butler"
    assert scotus["Sticker"] == "Associate Justice"
    assert (scotus.get("Sidecar") or {}).get("correlate") == "fjc:1378641"
    assert (scotus.get("Sidecar") or {}).get("bioguide_id") in (None, "")
    assert (scotus.get("Sidecar") or {}).get("wiki_page") == "Pierce_Butler_(justice)"
    assert not any(r.get("ProspectusID") == SENATOR_PID and r.get("Sticker") == "Associate Justice" for r in appointed["records"])

    edges = json.loads(
        (REPO / "packs/usg_appointed_holders/holders_judicial_scotus.json").read_text(encoding="utf-8")
    )
    edge = next(r for r in edges["records"] if r.get("ProspectusID") == EDGE_PID)
    assert edge["from_prospectus_id"] == SCOTUS_PID
    assert edge["DoB"] == "1922-12-21"


def test_no_fjc_bracket_names_in_appointed_people() -> None:
    bracket = re.compile(r"\[")
    bad = []
    for path in (REPO / "packs/usg_appointed_holders").glob("people_*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for rec in doc.get("records") or []:
            if rec.get("VertexType") != "Person":
                continue
            blob = f"{rec.get('Name')}|{rec.get('GivenName')}|{(rec.get('Sidecar') or {}).get('raw')}"
            if bracket.search(blob or ""):
                bad.append(rec.get("ProspectusID"))
    assert bad == []
