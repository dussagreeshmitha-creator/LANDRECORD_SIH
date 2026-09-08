from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

NAME_THRESHOLD = 85
BOUNDARY_THRESHOLD = 78
AREA_TOLERANCE = 0.03


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def _norm_id(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm(value))


def _ratio(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def _token_set_ratio(a: str, b: str) -> int:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return _ratio(a, b)
    inter = " ".join(sorted(ta & tb))
    return max(_ratio(a, b), _ratio(" ".join(sorted(ta)), " ".join(sorted(tb))), _ratio(inter, a), _ratio(inter, b))


def _to_float(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", str(value))
    return float(match.group(0)) if match else None


def _check_text(declared: str | None, extracted: str | None, threshold: int) -> dict[str, Any]:
    d, e = _norm(declared), _norm(extracted)
    if not d and not e:
        return {"status": "missing", "score": 0, "message": "No value on either side"}
    if not d:
        return {"status": "review", "score": 0, "message": "Declared value not provided"}
    if not e:
        return {"status": "mismatch", "score": 0, "message": "Could not extract this field from the document"}
    score = _token_set_ratio(d, e)
    if score >= threshold:
        return {"status": "match", "score": score, "message": "Values align"}
    return {"status": "mismatch", "score": score, "message": "Names or labels do not match"}


def _check_id(declared: str | None, extracted: str | None, label: str) -> dict[str, Any]:
    d, e = _norm_id(declared), _norm_id(extracted)
    if not d and not e:
        return {"status": "missing", "score": 0, "message": f"No {label} found"}
    if not e:
        return {"status": "mismatch", "score": 0, "message": f"{label} missing in document"}
    if not d:
        return {"status": "review", "score": 0, "message": f"Declared {label} not provided"}
    if d == e:
        return {"status": "match", "score": 100, "message": f"{label} matches"}
    return {"status": "mismatch", "score": _ratio(d, e), "message": f"{label} differs"}


def _check_area(declared: str | None, extracted: str | None) -> dict[str, Any]:
    d, e = _to_float(declared), _to_float(extracted)
    if d is None and e is None:
        return {"status": "missing", "score": 0, "message": "Area not available"}
    if e is None:
        return {"status": "mismatch", "score": 0, "message": "Area not extracted from document"}
    if d is None:
        return {"status": "review", "score": 0, "message": "Declared area not provided"}
    if d == 0:
        return {"status": "mismatch", "score": 0, "message": "Declared area is zero"}
    delta = abs(d - e) / d
    if delta <= AREA_TOLERANCE:
        return {"status": "match", "score": 100, "message": f"Area within {AREA_TOLERANCE * 100:.0f}% tolerance"}
    return {
        "status": "mismatch",
        "score": max(0, int(100 - delta * 100)),
        "message": f"Area differs by {delta * 100:.1f}%",
    }


def validate_record(declared: dict[str, str | None], extracted: dict[str, str | None]) -> dict[str, Any]:
    checks = {
        "owner_name": _check_text(declared.get("owner_name"), extracted.get("owner_name"), NAME_THRESHOLD),
        "survey_number": _check_id(declared.get("survey_number"), extracted.get("survey_number"), "Survey number"),
        "patta_number": _check_id(declared.get("patta_number"), extracted.get("patta_number"), "Patta number"),
        "land_area": _check_area(declared.get("land_area"), extracted.get("land_area")),
        "land_classification": _check_text(
            declared.get("land_classification"), extracted.get("land_classification"), NAME_THRESHOLD
        ),
        "record_date": _check_id(declared.get("record_date"), extracted.get("record_date"), "Date"),
        "north": _check_text(declared.get("north"), extracted.get("north"), BOUNDARY_THRESHOLD),
        "south": _check_text(declared.get("south"), extracted.get("south"), BOUNDARY_THRESHOLD),
        "east": _check_text(declared.get("east"), extracted.get("east"), BOUNDARY_THRESHOLD),
        "west": _check_text(declared.get("west"), extracted.get("west"), BOUNDARY_THRESHOLD),
    }
    statuses = [item["status"] for item in checks.values()]
    mismatch_count = statuses.count("mismatch")
    match_count = statuses.count("match")
    if mismatch_count:
        overall = "mismatch"
    elif match_count and statuses.count("missing") < len(checks):
        overall = "valid" if "review" not in statuses else "review"
    else:
        overall = "review"

    confidence = int(sum(item["score"] for item in checks.values()) / max(len(checks), 1))
    return {
        "overall": overall,
        "confidence": confidence,
        "mismatch_count": mismatch_count,
        "match_count": match_count,
        "checks": checks,
    }
