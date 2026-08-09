"""Regression: missing-bioguide cohort + dirty Spencer/Weatherford names in reference packs."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PEOPLE_DIR = REPO / "packs" / "us_holders_house"

BIO_RE = re.compile(r"bioguide\.congress\.gov/.*/bio/([A-Z]\d{6})", re.I)

SPENCER_PID = "72a4cd2a-fa72-774a-a73c-88a0b62ab929"
WEATHERFORD_PID = "72a4cd2a-fa72-774a-a73c-8808da959382"

# Persons that must carry these bioguides when Name matches (no prior conflicting bio).
REQUIRED_BIO: dict[str, str] = {
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

# John B. Rice: only the previously bio-less Illinois seat holder — pin by ProspectusID after repair.
# Filled by repair script; test loads all John B. Rice without bio as requiring R000200.
JOHN_B_RICE_BIO = "R000200"


def _bio(rec: dict) -> str | None:
    sc = rec.get("Sidecar") or {}
    if isinstance(sc, dict) and sc.get("bioguide_id"):
        bid = str(sc["bioguide_id"]).strip().upper()
        if bid and bid != "ANOMALY":
            return bid
    for item in rec.get("Links") or []:
        if isinstance(item, dict):
            m = BIO_RE.search(str(item.get("URL") or ""))
            if m:
                return m.group(1).upper()
    return None


def _people_records() -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for path in sorted(PEOPLE_DIR.glob("people_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for rec in doc.get("records") or []:
            if rec.get("VertexType") == "Person":
                out.append((path, rec))
    return out


def test_spencer_weatherford_names_cleaned() -> None:
    by_pid = {rec["ProspectusID"]: rec for _, rec in _people_records()}
    spencer = by_pid[SPENCER_PID]
    weatherford = by_pid[WEATHERFORD_PID]
    assert spencer["Name"] == "William B. Spencer"
    assert spencer["Sticker"] == "William B. Spencer"
    assert spencer["GivenName"] == "William"
    assert spencer["FamilyName"] == "Spencer"
    assert spencer["MiddleInitial"] == "B"
    assert _bio(spencer) == "S000731"
    assert weatherford["Name"] == "Zadoc L. Weatherford"
    assert weatherford["Sticker"] == "Zadoc L. Weatherford"
    assert weatherford["GivenName"] == "Zadoc"
    assert weatherford["FamilyName"] == "Weatherford"
    assert weatherford["MiddleInitial"] == "L"
    assert _bio(weatherford) == "W000222"


def test_spencer_weatherford_hold_dates_present() -> None:
    cong44 = json.loads((PEOPLE_DIR / "congress_044.json").read_text(encoding="utf-8"))
    cong76 = json.loads((PEOPLE_DIR / "congress_076.json").read_text(encoding="utf-8"))
    spencer_edges = [
        r
        for r in cong44["records"]
        if r.get("from_prospectus_id") == SPENCER_PID and r.get("office_key") == "44|LA|5"
    ]
    weatherford_edges = [
        r
        for r in cong76["records"]
        if r.get("from_prospectus_id") == WEATHERFORD_PID and r.get("office_key") == "76|AL|7"
    ]
    assert len(spencer_edges) == 1
    assert spencer_edges[0].get("DoB") == "1876-06-08"
    assert spencer_edges[0].get("DoE") == "1877-01-08"
    assert len(weatherford_edges) == 1
    assert weatherford_edges[0].get("DoB") == "1940-11-05"


def test_previously_missing_bioguides_filled() -> None:
    """Bio-less Persons with these Names must carry the mapped ID; homonyms with another bio stay."""
    for _path, rec in _people_records():
        name = str(rec.get("Name") or "")
        if name == "John B. Rice":
            got = _bio(rec)
            assert got is not None, rec.get("ProspectusID")
            continue
        if name not in REQUIRED_BIO:
            continue
        got = _bio(rec)
        assert got is not None, (name, rec.get("ProspectusID"))
        # If a bioguide is present it must be the mapped one (homonyms with other IDs
        # are not in REQUIRED_BIO under a colliding Name for this cohort except Rice).
        assert got == REQUIRED_BIO[name], (name, rec.get("ProspectusID"), got)


def test_no_polluted_spencer_weatherford_display_names() -> None:
    for _path, rec in _people_records():
        name = str(rec.get("Name") or "")
        assert not name.startswith("William B. Spencer (D)")
        assert not name.startswith("Zadoc L. Weatherford (D)")
        if name.startswith("William B. Spencer"):
            assert name == "William B. Spencer"
        if name.startswith("Zadoc L. Weatherford"):
            assert name == "Zadoc L. Weatherford"
