from __future__ import annotations

import re

from ..core import Footnote
from .Constants import _FOOTNOTE_RE


def collect_page_footnotes(
    lines: list[tuple[int, str]],
) -> dict[int, list[Footnote]]:
    """Build {page_number: [Footnote, ...]} from all footnote lines."""
    pool: dict[int, list[Footnote]] = {}
    for pg, ln in lines:
        if _FOOTNOTE_RE.match(ln):
            if m := re.match(r"^(\d+)\s*[-\u2013]\s*(.+)$", ln):
                pool.setdefault(pg, []).append(
                    Footnote(marker=m.group(1), text=m.group(2).strip())
                )
    return pool


def match_article_footnotes(
    lines: list[tuple[int, str]],
    page_footnotes: dict[int, list[Footnote]],
) -> list[Footnote]:
    """Return footnotes referenced by amendment markers in article text."""
    raw = " ".join(ln for _, ln in lines if not _FOOTNOTE_RE.match(ln))
    used_markers = set(re.findall(r"(\d+)\[", raw))
    if not used_markers:
        return []
    footnotes: list[Footnote] = []
    for pg in {pg for pg, _ in lines}:
        for fn in page_footnotes.get(pg, []):
            if fn.marker in used_markers:
                footnotes.append(fn)
    footnotes.sort(key=lambda fn: int(fn.marker))
    return footnotes
