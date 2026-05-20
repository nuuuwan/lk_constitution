from __future__ import annotations

import re
from pathlib import Path

_PDF_PATH = Path("data/original_data/constitution.pdf")
_OUTPUT_DIR = Path("data/parsed")

# Lines matching any of these patterns are page headers / footers
_NOISE_PATTERNS = [
    re.compile(r"^[xivXIV\s]+$", re.IGNORECASE),  # Roman numeral page labels
    re.compile(r"^\d+$"),  # bare page numbers
    re.compile(
        r"The Constitution of the Democratic Socialist Republic",
        re.IGNORECASE,
    ),
]

# Paragraph break markers in the preamble
_PARA_SPLITS = [
    re.compile(r"(?<=:)\s+(?=WE,\s)"),
    re.compile(r",\s+(?=do hereby adopt and enact)"),
]

# Chapter / article structure patterns
_CHAPTER_RE = re.compile(r"^(?:\d+\[)?CHAPTER\s+([IVXLC]+)\s*([A-Z])?\s*\]?$")
_ARTICLE_RE = re.compile(
    r"^(?:(?:\d+\[)?(?:[A-Za-z][A-Za-z]*(?: [A-Za-z][A-Za-z]*){0,3})?\s*)?"
    r"(?P<num>\d+[A-Z]?)\.[\s\u00a0]+"
)
# Footnote lines: "16 - Substituted by the..."
_FOOTNOTE_RE = re.compile(
    r"^\d+\s*[-\u2013]\s*(?:Substituted|Inserted|Repealed|Added|Amended"
    r"|Omitted|Deleted|Replaced)",
    re.IGNORECASE,
)
_AMEND_REF_RE = re.compile(r"\d+\[|\]")
_NUM_CLAUSE_RE = re.compile(r"\(([1-9][0-9]?)\)\s+")
_ALPHA_CLAUSE_RE = re.compile(r"\(([a-hj-uw-z])\)\s+")
_BODY_END_RE = re.compile(r"Other Consequential Amendments", re.IGNORECASE)

# Column x-boundaries separating body text from marginalia column.
# Odd (right-hand) pages: marginalia is to the right of the body.
# Even (left-hand) pages: marginalia is to the left of the body.
_MARGIN_X_ODD = 340.0
_MARGIN_X_EVEN = 165.0
# Vertical span considered the top header / bottom footer area of a page.
_PAGE_HEADER_BOTTOM = 75.0
_PAGE_FOOTER_TOP = 680.0
# x0 range that article-number words occupy in the body column.
_ART_X_ODD = (85.0, 135.0)
_ART_X_EVEN = (165.0, 220.0)
# A word that looks like a bare article number, e.g. "1.", "14A.", "111J."
_ART_NUM_WORD_RE = re.compile(r"^\d+[A-Z]?\.$")

_ROMAN_VALUES: dict[str, int] = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
}
