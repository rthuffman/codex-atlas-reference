"""Carefully clean polluted Person display/name-part fields in reference packs.

Strategy:
- Start from git HEAD for the three previously over-cleaned people packs.
- Strip only proven pollution (leading dash, party tags, from-dates, trailing commas).
- Preserve middle initials, Jr/Sr, particles (du/van), and multi-word middles.
- Fix a small set of known structured-field corruptions by ProspectusID.
- Normalize U+2019 → ASCII apostrophe in Person name-related strings.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Files that were over-cleaned; restore from HEAD then re-apply.
RESTORE_AND_CLEAN = [
    "packs/us_holders_house/people_post_reconstruction_certified.json",
    "packs/us_holders_house/people_pre_civil_war.json",
    "packs/us_holders_senate/people_post_reconstruction_certified.json",
]

# Additional files to touch without restore (structured-only / curly apostrophe).
EXTRA_SCAN = [
    "packs/us_holders_senate/people_pre_civil_war.json",
    "packs/us_holders_house/people_civil_war.json",
]

# Proven structured corruptions (ask if expanding beyond this table).
STRUCTURED_FIXES: dict[str, dict] = {
    # Pierce Butler — Name/Sticker already clean; parts polluted by resignation/party text.
    "72a4cd2a-fa72-774a-a73c-8821e260a7b7": {
        "GivenName": "Pierce",
        "FamilyName": "Butler",
        "drop_MiddleInitial": True,
        "Sidecar": {
            "raw": "Pierce Butler",
            "drop_middle": True,
        },
    },
    # George Hearst — strip party/dates; family is Hearst.
    "72a4cd2a-fa72-774a-a73c-889446680430": {
        "Name": "George Hearst",
        "Sticker": "George Hearst",
        "GivenName": "George",
        "FamilyName": "Hearst",
        "drop_MiddleInitial": True,
        "Sidecar": {
            "raw": "George Hearst",
            "middle": None,  # clear bad middle
            "drop_middle": True,
        },
    },
    # Henry A. du Pont — keep particle + family.
    "72a4cd2a-fa72-774a-a73c-88973ac135e2": {
        "Name": "Henry A. du Pont",
        "Sticker": "Henry A. du Pont",
        "GivenName": "Henry",
        "FamilyName": "du Pont",
        "MiddleInitial": "A",
        "Sidecar": {
            "raw": "Henry A. du Pont",
            "middle": "A.",
            "particle": "du",
        },
    },
    # Kenneth D. McKellar — strip trailing (D).
    "72a4cd2a-fa72-774a-a73c-88ec7ee3ede2": {
        "Name": "Kenneth D. McKellar",
        "Sticker": "Kenneth D. McKellar",
        "GivenName": "Kenneth",
        "FamilyName": "McKellar",
        "MiddleInitial": "D",
        "Sidecar": {
            "raw": "Kenneth D. McKellar",
            "middle": "D.",
        },
    },
    # Richard F. Pettigrew — Name/Sticker already clean; parts polluted.
    "72a4cd2a-fa72-774a-a73c-882265d1b41d": {
        "GivenName": "Richard",
        "FamilyName": "Pettigrew",
        "MiddleInitial": "F",
        "Sidecar": {
            "raw": "Richard F. Pettigrew",
            "middle": "F.",
        },
    },
    # Claude L'Engle — ASCII apostrophe + structured fields present in pack.
    "72a4cd2a-fa72-774a-a73c-8808ad8d8987": {
        "Name": "Claude L'Engle",
        "Sticker": "Claude L'Engle",
        "GivenName": "Claude",
        "FamilyName": "L'Engle",
        "Sidecar": {
            "raw": "Claude L'Engle",
        },
    },
}

# Display pollution: leading dash, parenthetical party/faction, from-date / change clauses, trailing comma.
DISPLAY_POLLUTION = re.compile(
    r"""(?ix)
    ^\s*-\s+                                      # leading list dash
    | \s*\((?:R|D|DR|W|FL|Soc\.?|Prog\.?|Proh\.?|Ind(?:\.\s*W)?)\s*\)\s*
    | \s*\((?:R|D)\)\s*
    | ,?\s*changed\s+to\s+\([^)]+\)(?:\s+on\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})?
    | \s+from\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}      # full from-date first
    | \s+from\s+[A-Za-z]+\s+\d{1,2}(?!\s*,)       # orphaned month-day after year strip
    | ,\s*$
    """
)

ROLE_STICKER = re.compile(
    r"(?i)\b(representing|represents the|occupied the chair|labor-member|management-member)\b"
    r"|^\s*Chair\s*\("
)

# Broader residual check after cleaning (should be empty for intentional party tags in Name).
RESIDUAL = re.compile(
    r"(?i)^\s*-\s+|\([A-Za-z .]+\)| from |changed to |\bProg\.|\bProh\.|\bSoc\.|,\s*$"
)

CURLY = "\u2019"
NAME_KEYS = ("Name", "Sticker", "GivenName", "FamilyName", "MiddleName", "MiddleInitial")


def _git_show(rel: str) -> bytes:
    return subprocess.check_output(["git", "show", f"HEAD:{rel}"], cwd=REPO)


def _clean_display(text: str) -> str:
    s = text
    # Iteratively strip known pollution fragments.
    prev = None
    while prev != s:
        prev = s
        s = DISPLAY_POLLUTION.sub(" ", s)
        s = re.sub(r"\s{2,}", " ", s).strip(" ,")
    # Collapse "Name ," leftovers
    s = re.sub(r"\s+,", ",", s).strip(" ,")
    return s


def _ascii_apostrophe(s: str) -> str:
    return s.replace(CURLY, "'")


def _apply_structured(rec: dict, fix: dict) -> bool:
    changed = False
    for key in ("Name", "Sticker", "GivenName", "FamilyName", "MiddleInitial"):
        if key in fix and rec.get(key) != fix[key]:
            rec[key] = fix[key]
            changed = True
    if fix.get("drop_MiddleInitial") and "MiddleInitial" in rec:
        del rec["MiddleInitial"]
        changed = True
    sc_fix = fix.get("Sidecar")
    if isinstance(sc_fix, dict):
        sc = rec.get("Sidecar")
        if not isinstance(sc, dict):
            sc = {}
            rec["Sidecar"] = sc
        for k, v in sc_fix.items():
            if k == "drop_middle":
                if "middle" in sc:
                    del sc["middle"]
                    changed = True
                continue
            if v is None:
                if k in sc:
                    del sc[k]
                    changed = True
                continue
            if sc.get(k) != v:
                sc[k] = v
                changed = True
    return changed


def _normalize_person_apostrophes(rec: dict) -> bool:
    changed = False
    for key in NAME_KEYS:
        val = rec.get(key)
        if isinstance(val, str) and CURLY in val:
            rec[key] = _ascii_apostrophe(val)
            changed = True
    sc = rec.get("Sidecar")
    if isinstance(sc, dict):
        for key in ("raw", "middle", "suffix", "particle"):
            val = sc.get(key)
            if isinstance(val, str) and CURLY in val:
                sc[key] = _ascii_apostrophe(val)
                changed = True
    return changed


def _clean_person(rec: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    changed = False
    pid = str(rec.get("ProspectusID") or "")

    if pid in STRUCTURED_FIXES:
        if _apply_structured(rec, STRUCTURED_FIXES[pid]):
            changed = True
            notes.append("structured_fix")

    for key in ("Name", "Sticker"):
        val = rec.get(key)
        if not isinstance(val, str) or not val.strip():
            continue
        # Keep intentional appointed/board role Stickers (not party/date pollution).
        if key == "Sticker" and ROLE_STICKER.search(val):
            if val.lstrip().startswith("-"):
                cleaned = _clean_display(val)
                if cleaned != val:
                    rec[key] = cleaned
                    changed = True
                    notes.append(f"{key}_dash")
            continue
        cleaned = _clean_display(val)
        if cleaned != val:
            rec[key] = cleaned
            changed = True
            notes.append(f"{key}_display")

    # Keep Sidecar.raw aligned with cleaned Name when raw still carries pollution.
    sc = rec.get("Sidecar")
    if isinstance(sc, dict):
        raw = sc.get("raw")
        name_now = rec.get("Name")
        if isinstance(raw, str) and isinstance(name_now, str) and raw != name_now:
            if RESIDUAL.search(raw) or raw.lstrip().startswith("-"):
                sc["raw"] = name_now
                changed = True
                notes.append("Sidecar.raw")


    # FamilyName trailing party / comma / date fragments only when clearly polluted.
    fn = rec.get("FamilyName")
    if isinstance(fn, str) and fn.strip():
        if re.search(r"(?i)\(|\)|,$|^\d+$|changed | from ", fn):
            cleaned = _clean_display(fn)
            # If cleaning emptied family, leave for structured table / ask later.
            if cleaned and cleaned != fn:
                rec["FamilyName"] = cleaned
                changed = True
                notes.append("FamilyName_display")

    if _normalize_person_apostrophes(rec):
        changed = True
        notes.append("apostrophe")

    return changed, notes


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def process_file(rel: str, *, restore: bool) -> dict:
    path = REPO / rel
    if restore:
        path.write_bytes(_git_show(rel))
    data = _load(path)
    recs = data.get("records") or []
    changed_n = 0
    details = []
    for rec in recs:
        if not isinstance(rec, dict) or rec.get("VertexType") != "Person":
            continue
        changed, notes = _clean_person(rec)
        if changed:
            changed_n += 1
            details.append(
                {
                    "pid": rec.get("ProspectusID"),
                    "Name": rec.get("Name"),
                    "notes": notes,
                }
            )
    # Bump slice reference_bundle_version placeholder; manifest owns release version.
    if changed_n:
        data["reference_bundle_version"] = "0.4.6-name-pollution"
    _save(path, data)
    return {"file": rel, "changed": changed_n, "details": details}


def residual_scan(paths: list[str]) -> list[dict]:
    bad = []
    for rel in paths:
        data = _load(REPO / rel)
        for rec in data.get("records") or []:
            if not isinstance(rec, dict) or rec.get("VertexType") != "Person":
                continue
            name = str(rec.get("Name") or "")
            sticker = str(rec.get("Sticker") or "")
            family = str(rec.get("FamilyName") or "")
            # Role stickers with parentheses are OK if Name is clean.
            name_bad = bool(RESIDUAL.search(name))
            family_bad = bool(re.search(r"(?i)\(|\)|,$|^\d+$", family))
            sticker_bad = False
            if RESIDUAL.search(sticker) and not ROLE_STICKER.search(sticker):
                sticker_bad = True
            if name_bad or family_bad or sticker_bad:
                bad.append(
                    {
                        "file": rel,
                        "pid": rec.get("ProspectusID"),
                        "Name": name,
                        "Sticker": sticker,
                        "FamilyName": family,
                    }
                )
    return bad


def main() -> None:
    results = []
    for rel in RESTORE_AND_CLEAN:
        results.append(process_file(rel, restore=True))
    for rel in EXTRA_SCAN:
        results.append(process_file(rel, restore=False))

    all_paths = sorted(set(RESTORE_AND_CLEAN + EXTRA_SCAN))
    residual = residual_scan(all_paths)
    out = {"results": results, "residual": residual}
    out_path = Path(r"D:\repos\artemis-workstation-session\working\pack_careful_clean_result.json")
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({r["file"]: r["changed"] for r in results}, indent=2))
    print("residual", len(residual))
    for b in residual[:20]:
        print(json.dumps(b, ensure_ascii=False))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
