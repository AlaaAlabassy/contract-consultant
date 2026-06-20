"""Extracts page-tagged text from a PDF contract.

PyMuPDF is the primary extractor (fast, keeps reading order well for
FIDIC-style numbered contracts). pdfplumber is used as a fallback for pages
where PyMuPDF returns suspiciously little text (often a sign of a table-heavy
page that PyMuPDF's plain text mode mangles).
"""

from __future__ import annotations

import io

import fitz  # PyMuPDF
import pdfplumber

MIN_CHARS_BEFORE_FALLBACK = 20


def parse_pdf_pages(file_bytes: bytes) -> list[tuple[int, str]]:
    """Returns a list of (page_number, page_text) tuples, 1-indexed."""
    pages: list[tuple[int, str]] = []
    weak_pages: list[int] = []

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if len(text.strip()) < MIN_CHARS_BEFORE_FALLBACK:
            weak_pages.append(i)
        pages.append((i, text))
    doc.close()

    if weak_pages:
        pages = _fallback_with_pdfplumber(file_bytes, pages, weak_pages)

    return pages


def _fallback_with_pdfplumber(
    file_bytes: bytes, pages: list[tuple[int, str]], weak_page_numbers: list[int]
) -> list[tuple[int, str]]:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num in weak_page_numbers:
            idx = page_num - 1
            if idx >= len(pdf.pages):
                continue
            text = pdf.pages[idx].extract_text() or ""
            if len(text.strip()) > len(pages[idx][1].strip()):
                pages[idx] = (page_num, text)
    return pages


def search_text_bbox(file_bytes: bytes, page_number: int, snippet: str) -> list[float] | None:
    """Finds the bounding box of `snippet` on `page_number` (1-indexed), for
    the Document Viewer's highlight-on-click feature. Returns [x0, y0, x1, y1]
    or None if not found."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if page_number < 1 or page_number > len(doc):
            return None
        page = doc[page_number - 1]
        rects = page.search_for(snippet.strip()[:200])
        if not rects:
            return None
        r = rects[0]
        return [r.x0, r.y0, r.x1, r.y1]
    finally:
        doc.close()
