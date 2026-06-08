"""extractor — 비텍스트 문서를 일반 텍스트로 추출 (인제스트 전처리).

지원: .pdf(pypdf) · .docx(python-docx) · .html/.htm(beautifulsoup4) ·
      이미지 .png/.jpg/.. (pytesseract OCR) · .md/.txt(그대로).
모든 의존성은 선택적 — 미설치 시 (None, 사유)로 graceful degrade 하여
router 가 해당 파일을 건너뛰고 명확히 보고하게 한다.
"""
from __future__ import annotations
import os
from typing import Optional, Tuple

__tool_version__ = "0.1.0"

PLAIN = {".md", ".txt"}
PDF = {".pdf"}
DOCX = {".docx"}
HTML = {".html", ".htm"}
IMAGE = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}

SUPPORTED = PLAIN | PDF | DOCX | HTML | IMAGE


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


def _ocr(path):
    import pytesseract
    from PIL import Image
    txt = pytesseract.image_to_string(Image.open(path)).strip()
    return (txt, "ocr") if txt else (None, "ocr: 인식된 텍스트 없음")
