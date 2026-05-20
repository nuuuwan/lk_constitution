from __future__ import annotations

from pathlib import Path

import pdfplumber

from .Constants import _MARGIN_X_EVEN, _MARGIN_X_ODD


def extract_full_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, full_text), ...] — uncropped."""
    with pdfplumber.open(pdf_path) as pdf:
        return [(p.page_number, p.extract_text() or "") for p in pdf.pages]


def extract_body_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, body_text), ...] cropped to body column.

    Strips the narrow outer-margin column so article text parsing is clean.
    """
    result: list[tuple[int, str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            pn = p.page_number
            h, w = p.height, p.width
            if pn % 2 == 1:  # odd page — margin on right
                body = p.crop((0, 0, _MARGIN_X_ODD, h))
            else:  # even page — margin on left
                body = p.crop((_MARGIN_X_EVEN, 0, w, h))
            result.append((pn, body.extract_text() or ""))
    return result
