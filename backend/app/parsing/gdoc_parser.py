"""Wraps a native Google Doc export (already plain text) into the same
(page_number, text) shape the other parsers return. Google Docs export has
no page boundaries either, so it is treated as a single page."""

from __future__ import annotations


def parse_gdoc_pages(exported_text: str) -> list[tuple[int, str]]:
    return [(1, exported_text)]
