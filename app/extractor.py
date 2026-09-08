"""OCR and field extraction for Indian land-record documents."""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from pypdf import PdfReader

logger = logging.getLogger(__name__)

TESSERACT_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]

FIELD_PATTERNS: dict[str, list[str]] = {
    "owner_name": [
        r"(?:name\s+of\s+(?:the\s+)?(?:owner|pattadar)|owner(?:'s)?\s*name|pattadar(?:\s*name)?)\s*[:\-]?\s*([A-Za-z][A-Za-z .']{1,80})",
        r"(?:sri|smt|shri)\.?\s+([A-Z][A-Za-z .']{2,60})",
    ],
    "survey_number": [
        r"(?:survey\s*(?:no\.?|number|#)|sy\.?\s*no\.?|s\.?\s*no\.?)\s*[:\-]?\s*([0-9]{1,6}(?:\s*[/\\-]\s*[0-9A-Za-z]+){0,3})",
    ],
    "patta_number": [
        r"(?:patta\s*(?:no\.?|number|#)|pattadar\s*passbook(?:\s*(?:no\.?|number)?)?|khata\s*(?:no\.?|number)?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]*\d[A-Z0-9\-\/]*)",
    ],
    "land_area": [
        r"(?:extent|total\s*area|land\s*area|area)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ha|hectare[s]?|acre[s]?|cent[s]?)?",
    ],
    "land_classification": [
        r"(?:land\s*classification|classification|type\s*of\s*land|land\s*type|nature\s*of\s*land)\s*[:\-]?\s*([A-Za-z][A-Za-z /,&-]{1,60})",
    ],
    "record_date": [
        r"(?:date\s*of\s*(?:issue|extract|document)|dated|date)\s*[:\-]?\s*([0-9]{1,2}[./\- ][0-9]{1,2}[./\- ][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
    ],
    "north": [r"(?:north(?:ern)?(?:\s*boundary)?|n\.?\s*b\.?)\s*[:\-]\s*(.+)"],
    "south": [r"(?:south(?:ern)?(?:\s*boundary)?|s\.?\s*b\.?)\s*[:\-]\s*(.+)"],
    "east": [r"(?:east(?:ern)?(?:\s*boundary)?|e\.?\s*b\.?)\s*[:\-]\s*(.+)"],
    "west": [r"(?:west(?:ern)?(?:\s*boundary)?|w\.?\s*b\.?)\s*[:\-]\s*(.+)"],
    "village": [r"(?:village|revenue\s*village)\s*[:\-]\s*([A-Za-z][A-Za-z .]{1,50})"],
    "taluk": [r"(?:taluk|taluka|tehsil)\s*[:\-]\s*([A-Za-z][A-Za-z .]{1,50})"],
    "district": [r"(?:district)\s*[:\-]\s*([A-Za-z][A-Za-z .]{1,50})"],
}

_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "owner_name": ("name of the owner", "name of owner", "owner name", "pattadar name", "pattadar"),
    "survey_number": ("survey number", "survey no", "sy no", "s no", "survey"),
    "patta_number": ("patta number", "patta no", "pattadar passbook", "khata number", "khata no", "patta"),
    "land_area": ("land area", "total area", "extent", "area"),
    "land_classification": (
        "land classification",
        "classification",
        "type of land",
        "land type",
        "nature of land",
    ),
    "record_date": ("date of issue", "date of extract", "dated", "date"),
    "north": ("north boundary", "northern boundary", "north"),
    "south": ("south boundary", "southern boundary", "south"),
    "east": ("east boundary", "eastern boundary", "east"),
    "west": ("west boundary", "western boundary", "west"),
    "village": ("revenue village", "village"),
    "taluk": ("taluka", "taluk", "tehsil"),
    "district": ("district",),
}

_PATTA_STOPWORDS = {
    "extract",
    "copy",
    "record",
    "document",
    "no",
    "number",
    "patta",
}

_TESSERACT_READY = False
_TESSERACT_ERROR = ""


def _configure_tesseract() -> tuple[bool, str]:
    global _TESSERACT_READY, _TESSERACT_ERROR
    try:
        import pytesseract
    except ImportError:
        _TESSERACT_READY = False
        _TESSERACT_ERROR = "pytesseract is not installed"
        return _TESSERACT_READY, _TESSERACT_ERROR

    env_cmd = os.environ.get("TESSERACT_CMD", "").strip()
    candidates: list[Path] = []
    if env_cmd:
        candidates.append(Path(env_cmd))
    which = shutil.which("tesseract")
    if which:
        candidates.append(Path(which))
    candidates.extend(TESSERACT_CANDIDATES)

    for path in candidates:
        if path.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            try:
                pytesseract.get_tesseract_version()
                _TESSERACT_READY = True
                _TESSERACT_ERROR = ""
                return _TESSERACT_READY, _TESSERACT_ERROR
            except Exception as exc:
                _TESSERACT_ERROR = str(exc)
                continue

    _TESSERACT_READY = False
    _TESSERACT_ERROR = (
        "Tesseract OCR was not found. Install it or set TESSERACT_CMD to tesseract.exe "
        r"(typical path: C:\Program Files\Tesseract-OCR\tesseract.exe)."
    )
    return _TESSERACT_READY, _TESSERACT_ERROR


_configure_tesseract()


def extract_text(path: Path) -> tuple[str, str]:
    """Return (text, engine_name)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _pdf_text(path)
        if text.strip():
            return text, "pdf-text"
        ocr, engine = _ocr_pdf_pages(path)
        return ocr, engine
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}:
        return _ocr_image(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore"), "plaintext"
    return "", "unsupported"


def _pdf_text(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        logger.warning("PDF text extract failed for %s: %s", path, exc)
        return ""


def _ocr_image(path: Path) -> tuple[str, str]:
    try:
        with Image.open(path) as raw:
            variants = _ocr_variants(raw)
            best_text = ""
            last_engine = "empty"
            for image in variants:
                text, engine = _ocr_pil(image)
                if engine == "ocr-missing":
                    return text, engine
                if len(text.strip()) > len(best_text.strip()):
                    best_text, last_engine = text, engine
            return best_text, last_engine if best_text.strip() else last_engine
    except Exception as exc:
        logger.exception("Failed to open image %s", path)
        return f"Could not read image: {exc}", "ocr-error"


def _ocr_pdf_pages(path: Path) -> tuple[str, str]:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        if not _TESSERACT_READY:
            return _TESSERACT_ERROR, "ocr-missing"
        return (
            "This PDF has no embedded text. Install pypdfium2 to OCR scanned PDF pages.",
            "ocr-unavailable",
        )

    if not _TESSERACT_READY:
        return _TESSERACT_ERROR, "ocr-missing"

    try:
        pdf = pdfium.PdfDocument(str(path))
        pages: list[str] = []
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=2)
            text, _engine = _ocr_pil(_prepare_image(bitmap.to_pil()))
            if text.strip():
                pages.append(text)
        joined = "\n\n".join(pages).strip()
        return joined, "ocr" if joined else "empty"
    except Exception as exc:
        logger.exception("PDF OCR failed for %s", path)
        return f"PDF OCR failed: {exc}", "ocr-error"


def _ocr_variants(raw: Image.Image) -> list[Image.Image]:
    base = ImageOps.exif_transpose(raw) or raw
    prepared = _prepare_image(base)
    binary = prepared.point(lambda p: 255 if p > 160 else 0)
    return [prepared, binary, _to_rgb(base)]


def _to_rgb(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image) or image
    if image.mode in {"RGBA", "P", "LA"}:
        background = Image.new("RGB", image.size, "white")
        converted = image.convert("RGBA")
        background.paste(converted, mask=converted.split()[-1])
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _prepare_image(image: Image.Image) -> Image.Image:
    image = _to_rgb(image)
    width, height = image.size
    longest = max(width, height)
    if longest < 1400:
        scale = 1400 / longest
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    gray = ImageOps.autocontrast(image.convert("L"))
    gray = gray.filter(ImageFilter.SHARPEN)
    return gray


def _ocr_pil(image: Image.Image) -> tuple[str, str]:
    ready, error = _configure_tesseract()
    if not ready:
        return error, "ocr-missing"
    import pytesseract

    configs = ["--oem 3 --psm 6", "--oem 3 --psm 4", "--oem 3 --psm 3"]
    best = ""
    last_error = ""
    for config in configs:
        try:
            text = pytesseract.image_to_string(image, lang="eng", config=config) or ""
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Tesseract failed (%s): %s", config, exc)
            continue
        if len(text.strip()) > len(best.strip()):
            best = text
    if best.strip():
        return best, "ocr"
    if last_error:
        return f"OCR failed: {last_error}", "ocr-error"
    return "", "empty"


def parse_fields(text: str) -> dict[str, str | None]:
    cleaned = _normalize_ocr_text(text)
    found: dict[str, str | None] = {key: None for key in FIELD_PATTERNS}
    found.update(_parse_labeled_lines(cleaned))

    for field, patterns in FIELD_PATTERNS.items():
        if found.get(field):
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, cleaned, flags=re.IGNORECASE | re.MULTILINE):
                value = _clean_value(field, match.group(1))
                if not value:
                    continue
                found[field] = value
                break
            if found.get(field):
                break

    sides = [found.get(key) for key in ("north", "south", "east", "west") if found.get(key)]
    found["boundaries"] = "; ".join(
        f"{label.title()}: {found[label]}" for label in ("north", "south", "east", "west") if found.get(label)
    ) if sides else None
    return found


def _normalize_ocr_text(text: str) -> str:
    cleaned = text.replace("\r", "\n").replace("：", ":").replace("|", "I")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return cleaned


def _parse_labeled_lines(text: str) -> dict[str, str | None]:
    found: dict[str, str | None] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip(" -•")
        if not line:
            continue
        label, value = "", ""
        if ":" in line:
            label, value = line.split(":", 1)
        elif "-" in line[:40]:
            label, value = line.split("-", 1)
        else:
            continue
        field = _match_label(label)
        if not field:
            continue
        cleaned = _clean_value(field, value)
        if cleaned and field not in found:
            found[field] = cleaned
    return found


def _match_label(label: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", label.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for field, aliases in _LABEL_ALIASES.items():
        for alias in aliases:
            if normalized == alias or normalized.startswith(alias + " "):
                return field
    return None


def _clean_value(field: str, value: str) -> str | None:
    value = re.sub(r"\s+", " ", value).strip(" .;,\n\t|-")
    if not value:
        return None
    if field == "patta_number" and value.lower() in _PATTA_STOPWORDS:
        return None
    if field == "land_area":
        match = re.search(r"[0-9]+(?:\.[0-9]+)?", value)
        return match.group(0) if match else None
    if field == "survey_number":
        value = re.sub(r"\s+", "", value)
    if field == "record_date":
        match = re.search(
            r"[0-9]{1,2}[./\-][0-9]{1,2}[./\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}",
            value,
        )
        return match.group(0) if match else value
    if field in {"north", "south", "east", "west"}:
        value = re.split(r"\s{2,}|\s+(?:north|south|east|west)\b", value, maxsplit=1, flags=re.I)[0]
        value = value.strip(" .;,\n\t|-")
    return value or None


def ensure_sample_scan(path: Path, source_text: str | None = None, *, force: bool = False) -> Path:
    """Create a readable sample land-record scan when the PNG is missing."""
    if not force and path.exists() and path.stat().st_size > 0:
        return path
    text = source_text or (
        "Revenue land record (patta copy)\n\n"
        "District: Tiruvallur\nTaluk: Tiruvallur\nVillage: Mappedu\n\n"
        "Name of the owner: R. Selvam\nSurvey No: 142/3B\nPatta No: TN-CHN-88421\n"
        "Extent: 1.24 hectares\nLand classification: Dry agricultural\nDate: 04-09-2026\n\n"
        "North boundary: Odai\nSouth boundary: Cart track\n"
        "East boundary: Survey 142/4\nWest boundary: Survey 142/2\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image = _render_document_image(text)
    image.save(path, format="PNG")
    return path


def _render_document_image(text: str) -> Image.Image:
    lines = text.splitlines() or [text]
    font = _document_font(28)
    padding = 48
    line_height = 42
    width = 1100
    height = padding * 2 + line_height * (len(lines) + 2)
    image = Image.new("RGB", (width, height), "#f4efe4")
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, width - 19, height - 19), outline="#1b1508", width=3)
    y = padding
    for line in lines:
        draw.text((padding, y), line, fill="#1b1508", font=font)
        y += line_height
    return image


def _document_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()
