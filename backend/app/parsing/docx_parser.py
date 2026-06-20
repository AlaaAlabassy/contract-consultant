"""Extracts text from a DOCX contract.

DOCX has no native page boundaries, so the whole document is treated as a
single logical "page" (page_number=1) for citation purposes - the clause
number itself remains the precise citation; only the page reference in the
Document Viewer falls back to "page 1" for these files.
"""

from __future__ import annotations

import io

from docx import Document


def parse_docx_pages(file_bytes: bytes) -> list[tuple[int, str]]:
    document = Document(io.BytesIO(file_bytes))
    text = "\n".join(p.text for p in document.paragraphs)
    return [(1, text)]
