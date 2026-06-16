from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from validate_reference_bundle import validate_bundle  # noqa: E402


PERSON_PID = "72a4cd2a-fa72-774a-a73c-72588abc0001"
EDGE_PID = "72a4cd2a-fa72-774a-a73c-72588abc0002"
OFFICE_PID = "72a4cd2a-fa72-774a-a73c-72587abc0003"


def _write_bundle(root: Path, *, bad_edge_endpoint: bool = False) -> None:
    pack_root = root / "packs" / "us_holders_house"
    pack_root.mkdir(parents=True)
    manifest = {
        "bundle_format_version": 1,
        "bundle_version": "1.0.0",
        "requires_seeds_bundle_version": "0.3.7",
        "requires_atlas_schema_version": "1.2.0",
        "release_tier": "major",
        "corpus_as_of": "2026-06-14",
        "packs": [{"pack_id": "us_holders_house", "pack_version": "1.0.0", "files": ["congress_001.json"]}],
    }
    records = [
        {
            "VertexType": "Person",
            "ProspectusID": PERSON_PID,
            "Name": "Rep. Example",
            "Sticker": "Example",
            "Blurb": "",
        },
        {
            "EdgeType": "HoldsSeat",
            "ProspectusID": EDGE_PID,
            "from_prospectus_id": PERSON_PID,
            "to_prospectus_id": "not-a-72587" if bad_edge_endpoint else OFFICE_PID,
            "Sticker": "Holds seat",
            "Blurb": "",
        },
    ]
    slice_doc = {
        "slice_format_version": 1,
        "slice_id": "us_holders_house_congress_001",
        "pack_id": "us_holders_house",
        "requires_seeds_bundle_version": "0.3.7",
        "reference_bundle_version": "1.0.0",
        "record_count": len(records),
        "records": records,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pack_root / "congress_001.json").write_text(json.dumps(slice_doc), encoding="utf-8")


def test_validate_bundle_accepts_reference_shape(tmp_path: Path) -> None:
    _write_bundle(tmp_path)
    assert validate_bundle(tmp_path) == []


def test_validate_bundle_rejects_gold_vacant_house_office_key(tmp_path: Path) -> None:
    pack_root = tmp_path / "packs" / "us_holders_house"
    pack_root.mkdir(parents=True)
    manifest = {
        "bundle_format_version": 1,
        "bundle_version": "0.1.0-civil-war.3",
        "requires_seeds_bundle_version": "0.3.7",
        "requires_atlas_schema_version": "1.2.0",
        "release_tier": "patch",
        "corpus_as_of": "2026-06-15",
        "packs": [{"pack_id": "us_holders_house", "pack_version": "0.1.0-civil-war.3", "files": ["congress_037.json"]}],
    }
    slice_doc = {
        "slice_format_version": 1,
        "slice_id": "us_holders_house_congress_037",
        "pack_id": "us_holders_house",
        "requires_seeds_bundle_version": "0.3.7",
        "reference_bundle_version": "0.1.0-civil-war.3",
        "record_count": 1,
        "records": [
            {
                "EdgeType": "HoldsSeat",
                "ProspectusID": EDGE_PID,
                "from_prospectus_id": PERSON_PID,
                "to_prospectus_id": OFFICE_PID,
                "office_key": "37|AL|1",
                "Sticker": "Rep. from AL-1, 37th Congress",
                "Blurb": "",
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pack_root / "congress_037.json").write_text(json.dumps(slice_doc), encoding="utf-8")
    errors = validate_bundle(tmp_path)
    assert any("policy A" in e for e in errors)


def test_validate_bundle_rejects_bad_structure_endpoint(tmp_path: Path) -> None:
    _write_bundle(tmp_path, bad_edge_endpoint=True)
    errors = validate_bundle(tmp_path)
    assert any("to_prospectus_id must be 72587" in e for e in errors)
