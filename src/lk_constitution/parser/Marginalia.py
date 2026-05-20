from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .Constants import (
    _ART_NUM_WORD_RE,
    _ART_X_EVEN,
    _ART_X_ODD,
    _MARGIN_X_EVEN,
    _MARGIN_X_ODD,
    _PAGE_FOOTER_TOP,
    _PAGE_HEADER_BOTTOM,
)


def build_marginalia_map(pdf_path: Path) -> dict[str, str]:
    """Return {article_number: description} from the outer-margin column."""
    marginalia: dict[str, str] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pn = page.page_number
            is_odd = pn % 2 == 1
            words = page.extract_words()
            if is_odd:
                body_words = [w for w in words if w["x0"] < _MARGIN_X_ODD]
                margin_words = [
                    w
                    for w in words
                    if w["x0"] >= _MARGIN_X_ODD
                    and _PAGE_HEADER_BOTTOM < w["top"] < _PAGE_FOOTER_TOP
                ]
                art_x_min, art_x_max = _ART_X_ODD
            else:
                body_words = [w for w in words if w["x0"] >= _MARGIN_X_EVEN]
                margin_words = [
                    w
                    for w in words
                    if w["x0"] < _MARGIN_X_EVEN
                    and _PAGE_HEADER_BOTTOM < w["top"] < _PAGE_FOOTER_TOP
                ]
                art_x_min, art_x_max = _ART_X_EVEN
            art_positions: list[tuple[str, float]] = []
            for w in body_words:
                if (
                    _ART_NUM_WORD_RE.match(w["text"])
                    and art_x_min <= w["x0"] <= art_x_max
                ):
                    art_positions.append((w["text"].rstrip("."), w["top"]))
            if not art_positions or not margin_words:
                continue
            for idx, (art_num, art_top) in enumerate(art_positions):
                next_top = (
                    art_positions[idx + 1][1]
                    if idx + 1 < len(art_positions)
                    else page.height
                )
                nearby = [
                    w
                    for w in margin_words
                    if art_top - 6 <= w["top"] < next_top
                ]
                if not nearby:
                    continue
                nearby.sort(key=lambda w: (w["top"], w["x0"]))
                pruned: list[dict] = [nearby[0]]
                for w in nearby[1:]:
                    if w["top"] - pruned[-1]["top"] > 25.0:
                        break
                    pruned.append(w)
                nearby = pruned
                lines: list[list[str]] = [[]]
                prev_top = nearby[0]["top"]
                for w in nearby:
                    if w["top"] - prev_top > 8.0:
                        lines.append([])
                    lines[-1].append(w["text"])
                    prev_top = w["top"]
                description = " ".join(
                    " ".join(line) for line in lines if line
                )
                description = re.sub(r"^\d+\[", "", description).strip()
                if not description:
                    continue
                if re.match(r"^\d+\s*[-\u2013]", description):
                    continue
                if description[0].islower():
                    continue
                marginalia.setdefault(art_num, description)
    return marginalia
