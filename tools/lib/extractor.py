"""extractor — 비텍스트 문서를 일반 텍스트로 추출 (인제스트 전처리).

지원: .pdf(pypdf) · .docx(python-docx) · .html/.htm(beautifulsoup4) ·
      .xlsx/.xlsm(openpyxl, 시트별 표) · 이미지 .png/.jpg/.. (pytesseract OCR) · .md/.txt(그대로).
모든 의존성은 선택적 — 미설치 시 (None, 사유)로 graceful degrade 하여
router 가 해당 파일을 건너뛰고 명확히 보고하게 한다.
"""
from __future__ import annotations
import os
from typing import Optional, Tuple

__tool_version__ = "0.2.0"

PLAIN = {".md", ".txt"}
PDF = {".pdf"}
DOCX = {".docx"}
HTML = {".html", ".htm"}
XLSX = {".xlsx", ".xlsm"}
IMAGE = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}

SUPPORTED = PLAIN | PDF | DOCX | HTML | XLSX | IMAGE


def is_supported(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in SUPPORTED


def extract(path: str) -> Tuple[Optional[str], str]:
    """(text, note) 반환. 실패/미지원 시 text=None, note=사유."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in PLAIN:
            return open(path, encoding="utf-8", errors="replace").read(), "plain"
        if ext in PDF:
            return _pdf(path)
        if ext in DOCX:
            return _docx(path)
        if ext in HTML:
            return _html(path)
        if ext in XLSX:
            return _xlsx(path)
        if ext in IMAGE:
            return _ocr(path)
        return None, f"unsupported ext: {ext}"
    except Exception as e:  # 라이브러리 부재/파싱 실패
        return None, f"{type(e).__name__}: {e}"


def _pdf(path):
    from pypdf import PdfReader
    r = PdfReader(path)
    parts = [(p.extract_text() or "") for p in r.pages]
    txt = "\n\n".join(parts).strip()
    return (txt, f"pdf:{len(r.pages)}p") if txt else (None, "pdf: 텍스트 없음(스캔본? OCR 필요)")


def _docx(path):
    import docx
    d = docx.Document(path)
    txt = "\n".join(p.text for p in d.paragraphs).strip()
    return (txt, "docx") if txt else (None, "docx: 빈 문서")


def _html(path):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    txt = soup.get_text("\n", strip=True)
    return (txt, "html") if txt else (None, "html: 텍스트 없음")


def _nonempty(v):
    return v is not None and str(v).strip() != ""


def _is_tabular(rows):
    """Header row + data rows shaped like a table → SQL is the accurate store. Else free-form."""
    if len(rows) < 2:
        return False
    if sum(1 for c in rows[0] if _nonempty(c)) < 2:        # need a real (≥2 col) header
        return False
    data = rows[1:]
    multi = sum(1 for r in data if sum(1 for c in r if _nonempty(c)) >= 2)
    return multi >= max(1, len(data) // 2)                 # most data rows are multi-column


def xlsx_sheets(path):
    """Per-sheet structured rows for hybrid routing (tabular→SQL, free-form→text).
    Returns (sheets, note); sheet = {title, rows:[[val,...]], tabular:bool}. Values preserved
    (numbers stay numeric) via iter_rows(values_only=True) — no `<ReadOnlyCell>` placeholders."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = []
    for ws in wb.worksheets:
        rows = [list(row) for row in ws.iter_rows(values_only=True) if any(_nonempty(c) for c in row)]
        if rows:
            sheets.append({"title": ws.title, "rows": rows, "tabular": _is_tabular(rows)})
    wb.close()
    return (sheets, "xlsx:%dsheets" % len(sheets)) if sheets else ([], "xlsx: 빈 워크북")


def _xlsx(path):
    """Excel → 시트별 표(markdown, full text). 핵심: iter_rows(values_only=True) 로 **셀 값**을 직접 받는다.
    (read_only 모드에서 셀 객체를 그대로 문자열화하면 `<ReadOnlyCell ...>` 가 박혀 값이 소실된다.)"""
    sheets, note = xlsx_sheets(path)
    parts = []
    for sh in sheets:
        parts.append("## %s" % sh["title"])
        parts.extend(" | ".join("" if c is None else str(c).strip() for c in r) for r in sh["rows"])
        parts.append("")
    txt = "\n".join(parts).strip()
    return (txt, note) if txt else (None, note)


def _ocr(path):
    import pytesseract
    from PIL import Image
    txt = pytesseract.image_to_string(Image.open(path)).strip()
    return (txt, "ocr") if txt else (None, "ocr: 인식된 텍스트 없음")
