"""Clause-aware chunker for construction/FIDIC-style English contracts.

Fixed-token-window chunking breaks a single clause across chunks and loses
the "which clause is this text from" link that citation-lock depends on.
Instead, this splits on clause-number boundaries detected via a cascade of
regex patterns, so every resulting chunk is already a citable unit: a
specific clause number + page number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHUNK_CHARS = 1800

# 1. Primary: numbered clause headers, e.g. "14.2 Advance Payment",
#    "Sub-Clause 20.1 Contractor's Claims".
PRIMARY_RE = re.compile(
    r"^(?:Sub-Clause\s+)?(\d{1,2}(?:\.\d{1,2}){0,3})\s+([A-Z][A-Za-z0-9 ,/&()'\-]{3,80})$"
)

# 2. Secondary: explicit "Clause"/"Article" keyword form, e.g.
#    "Clause 14.2: Advance Payment", "Article 20 - Claims".
SECONDARY_RE = re.compile(
    r"^(?:Clause|Article)\s+(\d{1,2}(?:\.\d{1,2}){0,3})[:.\-]?\s*(.*)$"
)

# 3. Fallback: bare numbered sub-clause continuation, e.g. "14.2.1 ...".
SUBCLAUSE_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\s")

# 4. Last resort: ALL-CAPS heading line (non-FIDIC documents).
ALLCAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z\s]{4,60}$")


@dataclass
class Chunk:
    clause_number: str | None
    clause_title: str | None
    page_number: int
    raw_text: str
    char_start: int
    char_end: int


@dataclass
class _Line:
    text: str
    page_number: int
    char_start: int
    char_end: int


def split_into_clauses(pages: list[tuple[int, str]]) -> list[Chunk]:
    lines = _flatten_to_lines(pages)
    chunks = _split_on_primary_secondary(lines)

    if not any(c.clause_number for c in chunks):
        chunks = _fallback_split(lines)

    return _enforce_max_size(chunks)


def _flatten_to_lines(pages: list[tuple[int, str]]) -> list[_Line]:
    lines: list[_Line] = []
    offset = 0
    for page_number, page_text in pages:
        for raw_line in page_text.split("\n"):
            line = raw_line.rstrip("\r")
            start = offset
            end = start + len(line)
            lines.append(_Line(text=line, page_number=page_number, char_start=start, char_end=end))
            offset = end + 1  # account for the join "\n"
    return lines


def _split_on_primary_secondary(lines: list[_Line]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_lines: list[_Line] = []
    current_number: str | None = None
    current_title: str | None = None

    def flush():
        if not current_lines:
            return
        text = "\n".join(l.text for l in current_lines).strip()
        if not text:
            return
        chunks.append(
            Chunk(
                clause_number=current_number,
                clause_title=current_title,
                page_number=current_lines[0].page_number,
                raw_text=text,
                char_start=current_lines[0].char_start,
                char_end=current_lines[-1].char_end,
            )
        )

    for line in lines:
        stripped = line.text.strip()
        match = PRIMARY_RE.match(stripped) or SECONDARY_RE.match(stripped)
        if match:
            flush()
            current_lines = [line]
            current_number = match.group(1)
            current_title = match.group(2).strip() if match.lastindex and match.lastindex >= 2 else None
            continue
        current_lines.append(line)

    flush()
    return chunks


def _fallback_split(lines: list[_Line]) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_lines: list[_Line] = []
    current_title: str | None = None
    paragraph_count = 0

    def flush():
        nonlocal paragraph_count
        if not current_lines:
            return
        text = "\n".join(l.text for l in current_lines).strip()
        if not text:
            return
        paragraph_count += 1
        title = current_title or f"Paragraph {paragraph_count}"
        chunks.append(
            Chunk(
                clause_number=None,
                clause_title=title,
                page_number=current_lines[0].page_number,
                raw_text=text,
                char_start=current_lines[0].char_start,
                char_end=current_lines[-1].char_end,
            )
        )

    for line in lines:
        stripped = line.text.strip()
        if ALLCAPS_HEADING_RE.match(stripped):
            flush()
            current_lines = [line]
            current_title = stripped
            continue
        if not stripped and current_lines:
            flush()
            current_lines = []
            current_title = None
            continue
        current_lines.append(line)

    flush()
    return chunks


def _enforce_max_size(chunks: list[Chunk]) -> list[Chunk]:
    """Splits any chunk over MAX_CHUNK_CHARS on sub-clause boundaries
    (e.g. 14.2.1, 14.2.2) rather than cutting mid-sentence, keeping each
    resulting piece linked to the parent clause number."""
    result: list[Chunk] = []
    for chunk in chunks:
        if len(chunk.raw_text) <= MAX_CHUNK_CHARS or chunk.clause_number is None:
            result.append(chunk)
            continue
        result.extend(_split_long_chunk(chunk))
    return result


def _split_long_chunk(chunk: Chunk) -> list[Chunk]:
    lines = chunk.raw_text.split("\n")
    pieces: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if SUBCLAUSE_RE.match(line.strip()) and current:
            pieces.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        pieces.append(current)

    if len(pieces) <= 1:
        return [chunk]

    sub_chunks = []
    offset = chunk.char_start
    for piece_lines in pieces:
        text = "\n".join(piece_lines).strip()
        if not text:
            continue
        match = SUBCLAUSE_RE.match(piece_lines[0].strip())
        number = match.group(1) if match else chunk.clause_number
        sub_chunks.append(
            Chunk(
                clause_number=number,
                clause_title=chunk.clause_title,
                page_number=chunk.page_number,
                raw_text=text,
                char_start=offset,
                char_end=offset + len(text),
            )
        )
        offset += len(text) + 1
    return sub_chunks
