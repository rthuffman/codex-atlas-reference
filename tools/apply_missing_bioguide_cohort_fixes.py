"""
Apply missing-bioguide + Spencer/Weatherford name fixes to codex-atlas-reference people packs.

Only fills bioguide when currently absent (does not overwrite a different existing bioguide,
e.g. a John B. Rice homonym). Cleans the two polluted display names by ProspectusID.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PEOPLE_DIR = REPO / "packs" / "us_holders_house"
LINK_DATE = "2026-08-09"

BIO_RE = re.compile(r"bioguide\.congress\.gov/.*/bio/([A-Z]\d{6})", re.I)

SPENCER_PID = "72a4cd2a-fa72-774a-a73c-88a0b62ab929"
WEATHERFORD_PID = "72a4cd2a-fa72-774a-a73c-8808da959382"

NAME_BIO: dict[str, str] = {
    "Charles A. Towne": "T000324",
    "Charles G. Ferris": "F000090",
    "Charles H. Turner": "T000415",
    "Charles W. Roark": "R000294",
    "David E. Evans": "E000237",
    "Ernest W. Marland": "M000138",
    "Frank Gillespie": "G000197",
    "George A. La Dow": "L000002",
    "George B. Shaw": "S000305",
    "George Ernest Foulkes": "F000317",
    "Henry W. Seymour": "S000267",
    "Howard W. Stull": "S001042",
    "James Henry McLean": "M000548",
    "James M. Hazlett": "H000421",
    "James P. Scoblick": "S000163",
    "John B. Rice": "R000200",
    "John C. Lehr": "L000228",
    "John S. Young": "Y000045",
    "Joseph F. Biddle": "B000442",
    "Joseph Marmaduke Pratt": "P000503",
    "Marsena E. Cutts": "C001032",
    "Michael Joseph Muldowney": "M001067",
    "Orrin D. Bleakley": "B000552",
    "Robert M. Leach": "L000171",
    "Thomas D. Singleton": "S000446",
    "William B. Spencer": "S000731",
    "William H. Stanton": "S000807",
    "William Kirk Kaynor": "K000024",
    "William Oscar Mulkey": "M001070",
    "Zadoc L. Weatherford": "W000222",
}

NAME_CLEANUPS = {
    SPENCER_PID: {
        "Name": "William B. Spencer",
        "GivenName": "William",
        "FamilyName": "Spencer",
        "MiddleInitial": "B",
        "sidecar_middle": "B",
        "bioguide": "S000731",
    },
    WEATHERFORD_PID: {
        "Name": "Zadoc L. Weatherford",
        "GivenName": "Zadoc",
        "FamilyName": "Weatherford",
        "MiddleInitial": "L",
        "sidecar_middle": "L",
        "bioguide": "W000222",
    },
}


def _bio(rec: dict) -> str | None:
    sc = rec.get("Sidecar") or {}
    if isinstance(sc, dict):
        bid = str(sc.get("bioguide_id") or "").strip().upper()
        if bid and bid != "ANOMALY":
            return bid
    for item in rec.get("Links") or []:
        if isinstance(item, dict):
            m = BIO_RE.search(str(item.get("URL") or ""))
            if m:
                return m.group(1).upper()
    return None


def _set_bioguide(rec: dict, *, name: str, bid: str) -> None:
    links = [x for x in (rec.get("Links") or []) if isinstance(x, dict)]
    links = [x for x in links if not BIO_RE.search(str(x.get("URL") or ""))]
    links.insert(
        0,
        {
            "URL": f"https://bioguide.congress.gov/search/bio/{bid}",
            "Blurb": "Biographical Directory of the United States Congress",
            "DateRetrieved": LINK_DATE,
            "IAFlag": False,
            "IALink": None,
        },
    )
    rec["Links"] = links
    sc = dict(rec.get("Sidecar") or {}) if isinstance(rec.get("Sidecar"), dict) else {"version": "0.1"}
    sc["bioguide_id"] = bid
    if "raw" not in sc:
        sc["raw"] = name
    if "name_source" not in sc:
        sc["name_source"] = "gold_explicit"
    rec["Sidecar"] = sc


def _clean_name(rec: dict, fix: dict) -> None:
    name = fix["Name"]
    rec["Name"] = name
    rec["Sticker"] = name
    rec["GivenName"] = fix["GivenName"]
    rec["FamilyName"] = fix["FamilyName"]
    rec["MiddleInitial"] = fix["MiddleInitial"]
    sc = dict(rec.get("Sidecar") or {}) if isinstance(rec.get("Sidecar"), dict) else {"version": "0.1"}
    sc["raw"] = name
    sc["middle"] = fix["sidecar_middle"]
    sc["name_source"] = "gold_explicit"
    sc.setdefault(
        "name_confidence",
        {"given": 1.0, "family": 1.0},
    )
    rec["Sidecar"] = sc
    _set_bioguide(rec, name=name, bid=fix["bioguide"])


def main() -> None:
    stats = {"files": 0, "name_cleanups": 0, "bioguides_added": 0, "skipped_existing_bio": 0}
    for path in sorted(PEOPLE_DIR.glob("people_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for rec in doc.get("records") or []:
            if rec.get("VertexType") != "Person":
                continue
            pid = str(rec.get("ProspectusID") or "")
            if pid in NAME_CLEANUPS:
                _clean_name(rec, NAME_CLEANUPS[pid])
                stats["name_cleanups"] += 1
                changed = True
                continue
            name = str(rec.get("Name") or "")
            expect = NAME_BIO.get(name)
            if not expect:
                continue
            existing = _bio(rec)
            if existing == expect:
                continue
            if existing is not None and existing != expect:
                # Homonym with a different bioguide — leave alone.
                stats["skipped_existing_bio"] += 1
                continue
            _set_bioguide(rec, name=name, bid=expect)
            stats["bioguides_added"] += 1
            changed = True
        if changed:
            path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            stats["files"] += 1
            print(f"wrote {path.name}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
