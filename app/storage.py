"""Simple JSON persistence for processed land records."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

LOCK = threading.Lock()
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "records.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _write(rows: list[dict[str, Any]]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def list_records() -> list[dict[str, Any]]:
    with LOCK:
        rows = _read()
    return sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)


def get_record(record_id: str) -> dict[str, Any] | None:
    for row in list_records():
        if row["id"] == record_id:
            return row
    return None


def save_record(payload: dict[str, Any]) -> dict[str, Any]:
    row = {"id": str(uuid4()), "created_at": _now(), **payload}
    with LOCK:
        rows = _read()
        rows.append(row)
        _write(rows)
    return row


def seed_if_empty() -> None:
    with LOCK:
        if _read():
            return
        _write(_demo_records())


def stats() -> dict[str, Any]:
    rows = list_records()
    overall = [r.get("validation", {}).get("overall") for r in rows]
    mismatches = sum(r.get("validation", {}).get("mismatch_count", 0) for r in rows)
    field_hits: dict[str, int] = {}
    for row in rows:
        for field, check in (row.get("validation") or {}).get("checks", {}).items():
            if check.get("status") == "mismatch":
                field_hits[field] = field_hits.get(field, 0) + 1
    return {
        "total": len(rows),
        "valid": overall.count("valid"),
        "mismatch": overall.count("mismatch"),
        "review": overall.count("review"),
        "field_mismatches": field_hits,
        "total_field_mismatches": mismatches,
    }


def _demo_records() -> list[dict[str, Any]]:
    samples = [
        {
            "filename": "patta_chennai_2041.pdf",
            "engine": "demo",
            "declared": {
                "owner_name": "R. Selvam",
                "survey_number": "142/3B",
                "patta_number": "TN-CHN-88421",
                "land_area": "1.24",
                "north": "Odai",
                "south": "Cart track",
                "east": "Survey 142/4",
                "west": "Survey 142/2",
                "village": "Mappedu",
                "taluk": "Tiruvallur",
                "district": "Tiruvallur",
            },
            "extracted": {
                "owner_name": "R Selvam",
                "survey_number": "142/3B",
                "patta_number": "TN-CHN-88421",
                "land_area": "1.24",
                "north": "Odai",
                "south": "Cart track",
                "east": "Survey 142/4",
                "west": "Survey 142/2",
                "village": "Mappedu",
                "taluk": "Tiruvallur",
                "district": "Tiruvallur",
            },
            "ocr_text": "DEMO RECORD — Patta matches registry.",
            "lat": 13.1436,
            "lng": 79.9082,
            "validation": {
                "overall": "valid",
                "confidence": 97,
                "mismatch_count": 0,
                "match_count": 8,
                "checks": {
                    "owner_name": {"status": "match", "score": 95, "message": "Values align"},
                    "survey_number": {"status": "match", "score": 100, "message": "Survey number matches"},
                    "patta_number": {"status": "match", "score": 100, "message": "Patta number matches"},
                    "land_area": {"status": "match", "score": 100, "message": "Area within 3% tolerance"},
                    "north": {"status": "match", "score": 100, "message": "Values align"},
                    "south": {"status": "match", "score": 100, "message": "Values align"},
                    "east": {"status": "match", "score": 100, "message": "Values align"},
                    "west": {"status": "match", "score": 100, "message": "Values align"},
                },
            },
        },
        {
            "filename": "survey_sketch_madurai.jpg",
            "engine": "demo",
            "declared": {
                "owner_name": "Lakshmi Narayanan",
                "survey_number": "88/1A",
                "patta_number": "TN-MDU-11092",
                "land_area": "2.10",
                "north": "Panchayat road",
                "south": "Channel",
                "east": "Temple land",
                "west": "Survey 87",
                "village": "Vadipatti",
                "taluk": "Vadipatti",
                "district": "Madurai",
            },
            "extracted": {
                "owner_name": "Laxmi Narayan",
                "survey_number": "88/1A",
                "patta_number": "TN-MDU-11902",
                "land_area": "1.62",
                "north": "Panchayat road",
                "south": "Channel",
                "east": "Private land",
                "west": "Survey 87",
                "village": "Vadipatti",
                "taluk": "Vadipatti",
                "district": "Madurai",
            },
            "ocr_text": "DEMO RECORD — owner, patta, area and east boundary disagree.",
            "lat": 10.0840,
            "lng": 78.0010,
            "validation": {
                "overall": "mismatch",
                "confidence": 62,
                "mismatch_count": 4,
                "match_count": 4,
                "checks": {
                    "owner_name": {"status": "mismatch", "score": 72, "message": "Names or labels do not match"},
                    "survey_number": {"status": "match", "score": 100, "message": "Survey number matches"},
                    "patta_number": {"status": "mismatch", "score": 88, "message": "Patta number differs"},
                    "land_area": {"status": "mismatch", "score": 77, "message": "Area differs by 22.9%"},
                    "north": {"status": "match", "score": 100, "message": "Values align"},
                    "south": {"status": "match", "score": 100, "message": "Values align"},
                    "east": {"status": "mismatch", "score": 45, "message": "Names or labels do not match"},
                    "west": {"status": "match", "score": 100, "message": "Values align"},
                },
            },
        },
        {
            "filename": "fmb_coimbatore.txt",
            "engine": "demo",
            "declared": {
                "owner_name": "K. Meenakshi",
                "survey_number": "12/6",
                "patta_number": "TN-CBE-55201",
                "land_area": "0.48",
                "north": "Survey 12/5",
                "south": "Survey 12/7",
                "east": "Natham",
                "west": "River poramboke",
                "village": "Sulur",
                "taluk": "Sulur",
                "district": "Coimbatore",
            },
            "extracted": {
                "owner_name": "K Meenakshi",
                "survey_number": "12/6",
                "patta_number": "TN-CBE-55201",
                "land_area": "0.48",
                "north": None,
                "south": "Survey 12/7",
                "east": "Natham",
                "west": "River poramboke",
                "village": "Sulur",
                "taluk": "Sulur",
                "district": "Coimbatore",
            },
            "ocr_text": "DEMO RECORD — north boundary not readable on scan.",
            "lat": 11.0240,
            "lng": 77.1250,
            "validation": {
                "overall": "review",
                "confidence": 84,
                "mismatch_count": 0,
                "match_count": 7,
                "checks": {
                    "owner_name": {"status": "match", "score": 96, "message": "Values align"},
                    "survey_number": {"status": "match", "score": 100, "message": "Survey number matches"},
                    "patta_number": {"status": "match", "score": 100, "message": "Patta number matches"},
                    "land_area": {"status": "match", "score": 100, "message": "Area within 3% tolerance"},
                    "north": {"status": "mismatch", "score": 0, "message": "Could not extract this field from the document"},
                    "south": {"status": "match", "score": 100, "message": "Values align"},
                    "east": {"status": "match", "score": 100, "message": "Values align"},
                    "west": {"status": "match", "score": 100, "message": "Values align"},
                },
            },
        },
    ]
    stamped = []
    for index, sample in enumerate(samples):
        stamped.append(
            {
                "id": f"demo-{index + 1}",
                "created_at": datetime(2026, 9, 4 + index, 8, 30, tzinfo=timezone.utc).isoformat(),
                **sample,
            }
        )
    return stamped
