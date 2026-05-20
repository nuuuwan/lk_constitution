from __future__ import annotations

import re
from datetime import datetime

from ..core import Preamble
from .Constants import _PARA_SPLITS


def parse_metadata(text: str) -> dict[str, str]:
    title = (
        "The Constitution of the Democratic Socialist" " Republic of Sri Lanka"
    )
    edition = ""
    if m := re.search(r"Revised Edition\s*[–\-]\s*(\d{4})", text):
        edition = f"Revised Edition – {m.group(1)}"
    amended_up_to = ""
    if m := re.search(
        r"As amended up to\s+(\d+)(?:st|nd|rd|th)\s+(\w+)\s+(\d{4})", text
    ):
        try:
            dt = datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y"
            )
            amended_up_to = dt.strftime("%Y-%m-%d")
        except ValueError:
            amended_up_to = m.group(3)
    last_amendment = ""
    if m := re.search(
        r"(Twenty[- ]?First|Twenty[- ]?Second|Nineteenth|Eighteenth)"
        r"\s+Amendment",
        text,
        re.IGNORECASE,
    ):
        last_amendment = f"{m.group(1)} Amendment"
    published_by = ""
    if m := re.search(r"Published by the ([^\n]+)", text):
        published_by = m.group(1).strip()
    return {
        "title": title,
        "edition": edition,
        "amended_up_to": amended_up_to,
        "last_amendment": last_amendment,
        "published_by": published_by,
    }


def parse_preamble(pages: list[tuple[int, str]]) -> Preamble:
    preamble_page: int | None = None
    raw_preamble = ""
    for page_num, text in pages:
        if "SVASTI" in text and preamble_page is None:
            preamble_page = page_num
            after_svasti = text.split("SVASTI", 1)[1]
            if m := re.search(r"\bCHAPTER\s*[-–]?\s*I\b", after_svasti):
                raw_preamble = after_svasti[: m.start()]
            else:
                raw_preamble = after_svasti
            if re.search(r"do hereby adopt and enact", raw_preamble):
                break
        elif preamble_page is not None:
            if m := re.search(r"\bCHAPTER\s*[-–]?\s*I\b", text):
                raw_preamble += "\n" + text[: m.start()]
                break
            raw_preamble += "\n" + text
    if not raw_preamble:
        raise ValueError("Could not locate preamble text in the PDF.")
    flat = re.sub(r"\s+", " ", raw_preamble).strip()
    segments = [flat]
    for pattern in _PARA_SPLITS:
        new_segments: list[str] = []
        for seg in segments:
            parts = pattern.split(seg, maxsplit=1)
            new_segments.extend(parts)
        segments = new_segments
    paragraphs = [s.strip() for s in segments if s.strip()]
    return Preamble(
        text_paragraphs=paragraphs,
        original_doc_page_num=preamble_page,
    )
