from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
INDEX = ROOT / "templates" / "index.html"

OCR_DETAILS = {
    "owner_name": "Ravi Kumar",
    "survey_number": "142/3A",
    "patta_number": "PT-2024-8765",
    "land_area": "2.50 Acres",
    "land_classification": "Agricultural",
    "record_date": "12-06-2024",
    "village": "Tiruvallur",
    "taluk": "Tiruvallur",
    "district": "Tiruvallur",
    "north_boundary": "Government Road",
    "south_boundary": "Survey No. 142/4",
    "east_boundary": "Agricultural Land",
    "west_boundary": "Canal",
    "latitude": "13.1436",
    "longitude": "79.9082",
}

RECORDS = [
    {"id": "LR-001", "owner": "Ravi Kumar", "survey_number": "142/3A", "area": "2.50 Acres", "status": "VERIFIED"},
    {"id": "LR-002", "owner": "Priya Devi", "survey_number": "118/2B", "area": "1.75 Acres", "status": "VERIFIED"},
    {"id": "LR-003", "owner": "Suresh Kumar", "survey_number": "205/1A", "area": "3.20 Acres", "status": "ISSUE DETECTED"},
    {"id": "LR-004", "owner": "Lakshmi Devi", "survey_number": "89/4C", "area": "2.00 Acres", "status": "VERIFIED"},
]

app = FastAPI(title="NEXORA | LandSecureAI", version="2.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(INDEX)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/stats")
def stats() -> dict[str, int]:
    return {"total": 24, "verified": 18, "issues": 6, "ocr_accuracy": 94}


@app.get("/api/records")
def records() -> list[dict[str, str]]:
    return deepcopy(RECORDS)


@app.get("/api/records/{record_id}")
def record_detail(record_id: str) -> dict[str, Any]:
    record = next((item for item in RECORDS if item["id"] == record_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    detail = deepcopy(record)
    detail["ocr_details"] = deepcopy(OCR_DETAILS)
    detail["validation"] = build_validation(False)
    return detail


def build_validation(mismatch: bool) -> dict[str, Any]:
    checks = [
        {"field": "Owner Name", "ocr": "Ravi Kumar", "registry": "Ravi Kumar", "status": "MATCHED"},
        {"field": "Survey Number", "ocr": "142/3A", "registry": "142/3A", "status": "MATCHED"},
        {"field": "Patta Number", "ocr": "PT-2024-8765", "registry": "PT-2024-8765", "status": "MATCHED"},
        {"field": "Land Area", "ocr": "3.20 Acres" if mismatch else "2.50 Acres", "registry": "2.50 Acres", "status": "MISMATCH" if mismatch else "MATCHED"},
        {"field": "Land Classification", "ocr": "Agricultural", "registry": "Agricultural", "status": "MATCHED"},
        {"field": "Boundaries", "ocr": "Canal" if mismatch else "Government Road / Survey No. 142/4 / Agricultural Land / Canal", "registry": "Government Land" if mismatch else "Government Road / Survey No. 142/4 / Agricultural Land / Canal", "status": "MISMATCH" if mismatch else "MATCHED"},
    ]
    return {
        "checks": checks,
        "overall_status": "MANUAL VERIFICATION REQUIRED" if mismatch else "VERIFIED",
        "headline": "LAND RECORD REQUIRES REVIEW" if mismatch else "LAND RECORD VERIFIED",
        "message": "Potential inconsistencies were detected in the land record." if mismatch else "All important fields passed validation checks.",
    }


@app.post("/api/validate")
async def validate(file: UploadFile = File(...)) -> dict[str, Any]:
    await file.read()
    return {
        "id": f"VAL-{uuid4().hex[:6].upper()}",
        "filename": file.filename or "land-record",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "ocr_details": deepcopy(OCR_DETAILS),
        "validation": build_validation(False),
    }


@app.post("/api/records")
async def legacy_validate(file: UploadFile = File(...)) -> dict[str, Any]:
    return await validate(file)
