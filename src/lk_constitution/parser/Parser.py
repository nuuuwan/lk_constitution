from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pdfplumber

from ..core import Article, Chapter, Clause, Constitution, Footnote, Preamble

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
# Paragraph 1 ends with ":"  before "WE,"
# Paragraph 2 ends with ","  before "do hereby adopt and enact"
_PARA_SPLITS = [
    re.compile(r"(?<=:)\s+(?=WE,\s)"),
    re.compile(r",\s+(?=do hereby adopt and enact)"),
]

# Chapter / article structure patterns
# Matches: [optional amendment_ref][CHAPTER [ROMAN][optional letter suffix]
_CHAPTER_RE = re.compile(r"^(?:\d+\[)?CHAPTER\s+([IVXLC]+)\s*([A-Z])?\s*\]?$")
# Matches: [optional amendment_ref[optional words]] article_number.
# Handles cases like "16[30.", "28[Powers 33.", "106[Constitution 111D.",
# and left-margin marginalia prefixes like "Freedom of 10.", "Citizenship 26."
_ARTICLE_RE = re.compile(
    r"^(?:(?:\d+\[)?(?:[A-Za-z][A-Za-z]*(?: [A-Za-z][A-Za-z]*){0,3})?\s*)?(?P<num>\d+[A-Z]?)\.[\s\u00a0]+"
)
# Footnote lines: "16 - Substituted by the..."
_FOOTNOTE_RE = re.compile(
    r"^\d+\s*[-\u2013]\s*(?:Substituted|Inserted|Repealed|Added|Amended"
    r"|Omitted|Deleted|Replaced)",
    re.IGNORECASE,
)
# Strip editorial amendment brackets from article/clause text
_AMEND_REF_RE = re.compile(r"\d+\[|\]")
# Top-level numeric clause marker: (1), (2), ... (99)
_NUM_CLAUSE_RE = re.compile(r"\(([1-9][0-9]?)\)\s+")
# Top-level alpha clause marker: (a)-(h) — avoid (i)/(v)/(x) (Roman numerals)
_ALPHA_CLAUSE_RE = re.compile(r"\(([a-hj-uw-z])\)\s+")
# Signals that the main constitution body has ended (schedules / appendix follow)
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

# ---- Roman numeral helpers -----------------------------------------------
_ROMAN_VALUES: dict[str, int] = {
    "I": 1, "V": 5, "X": 10, "L": 50, "C": 100
}


def _roman_to_int(s: str) -> int:
    result, prev = 0, 0
    for ch in reversed(s.upper()):
        val = _ROMAN_VALUES[ch]
        result += val if val >= prev else -val
        prev = val
    return result


def _decimal_chapter_num(roman: str, suffix: str) -> str:
    """Convert e.g. roman='XVI', suffix='A' → '016A'."""
    return f"{_roman_to_int(roman):03d}{suffix}"


def _is_noise(line: str) -> bool:
    return any(p.search(line) for p in _NOISE_PATTERNS)


def _clean_paragraph(raw: str) -> str:
    lines = [
        ln.strip()
        for ln in raw.splitlines()
        if ln.strip() and not _is_noise(ln.strip())
    ]
    return re.sub(r" {2,}", " ", " ".join(lines)).strip()


class Parser:
    def __init__(self, pdf_path: Path = _PDF_PATH):
        self.pdf_path = Path(pdf_path)
        self._pages: list[tuple[int, str]] | None = None
        self._body_pages: list[tuple[int, str]] | None = None

    # ------------------------------------------------------------------
    # Page extraction
    # ------------------------------------------------------------------

    def _extract_pages(self) -> list[tuple[int, str]]:
        """Return [(pdf_page_number, full_text), ...] — uncropped.

        Used for metadata and preamble parsing, where centred text may
        span the margin boundary.
        """
        if self._pages is None:
            with pdfplumber.open(self.pdf_path) as pdf:
                self._pages = [
                    (p.page_number, p.extract_text() or "")
                    for p in pdf.pages
                ]
        return self._pages

    def _extract_body_pages(self) -> list[tuple[int, str]]:
        """Return [(pdf_page_number, body_text), ...] cropped to body column.

        Strips the narrow outer-margin column (which contains article
        marginalia) so that article text parsing is clean.
        """
        if self._body_pages is None:
            result: list[tuple[int, str]] = []
            with pdfplumber.open(self.pdf_path) as pdf:
                for p in pdf.pages:
                    pn = p.page_number
                    h = p.height
                    w = p.width
                    if pn % 2 == 1:  # odd page — margin on right
                        body = p.crop((0, 0, _MARGIN_X_ODD, h))
                    else:            # even page — margin on left
                        body = p.crop((_MARGIN_X_EVEN, 0, w, h))
                    result.append((pn, body.extract_text() or ""))
            self._body_pages = result
        return self._body_pages

    def _build_marginalia_map(self) -> dict[str, str]:
        """Return {article_number: description_text} extracted from the
        narrow outer-margin column on each page using word coordinates.
        """
        marginalia: dict[str, str] = {}
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                pn = page.page_number
                is_odd = pn % 2 == 1
                words = page.extract_words()

                if is_odd:
                    body_words = [w for w in words if w["x0"] < _MARGIN_X_ODD]
                    margin_words = [
                        w for w in words
                        if w["x0"] >= _MARGIN_X_ODD
                        and _PAGE_HEADER_BOTTOM < w["top"] < _PAGE_FOOTER_TOP
                    ]
                    art_x_min, art_x_max = _ART_X_ODD
                else:
                    body_words = [w for w in words if w["x0"] >= _MARGIN_X_EVEN]
                    margin_words = [
                        w for w in words
                        if w["x0"] < _MARGIN_X_EVEN
                        and _PAGE_HEADER_BOTTOM < w["top"] < _PAGE_FOOTER_TOP
                    ]
                    art_x_min, art_x_max = _ART_X_EVEN

                # Find article-number word positions in the body column.
                art_positions: list[tuple[str, float]] = []
                for w in body_words:
                    if (
                        _ART_NUM_WORD_RE.match(w["text"])
                        and art_x_min <= w["x0"] <= art_x_max
                    ):
                        art_positions.append((w["text"].rstrip("."), w["top"]))

                if not art_positions or not margin_words:
                    continue

                # For each article, gather margin words in its vertical range.
                for idx, (art_num, art_top) in enumerate(art_positions):
                    next_top = (
                        art_positions[idx + 1][1]
                        if idx + 1 < len(art_positions)
                        else page.height
                    )
                    nearby = [
                        w for w in margin_words
                        if art_top - 6 <= w["top"] < next_top
                    ]
                    if not nearby:
                        continue

                    nearby.sort(key=lambda w: (w["top"], w["x0"]))

                    # Stop at the first large vertical gap (> 25pt) so that
                    # footnote markers at the bottom of the page are not
                    # mistaken for the last article's description.
                    pruned: list[dict] = [nearby[0]]
                    for w in nearby[1:]:
                        if w["top"] - pruned[-1]["top"] > 25.0:
                            break
                        pruned.append(w)
                    nearby = pruned

                    # Group words into text lines by vertical proximity.
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
                    # Strip leading amendment-reference markers, e.g. "45[Title"
                    description = re.sub(r"^\d+\[", "", description).strip()
                    # Discard footnote references (start with "N -") and
                    # footnote continuations (start with a lowercase letter).
                    if not description:
                        continue
                    if re.match(r"^\d+\s*[-\u2013]", description):
                        continue
                    if description[0].islower():
                        continue

                    # setdefault: first valid occurrence wins over later
                    # reuse of the same number in schedule list items.
                    marginalia.setdefault(art_num, description)
        return marginalia

    def _full_text(self) -> str:
        return "\n".join(text for _, text in self._extract_pages())

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _parse_metadata(self, text: str) -> dict[str, str]:
        title = "The Constitution of the Democratic Socialist Republic of Sri Lanka"

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

    # ------------------------------------------------------------------
    # Preamble
    # ------------------------------------------------------------------

    def _parse_preamble(self, pages: list[tuple[int, str]]) -> Preamble:
        preamble_page: int | None = None
        raw_preamble = ""

        for page_num, text in pages:
            if "SVASTI" in text and preamble_page is None:
                preamble_page = page_num
                # Take everything after the SVASTI heading line
                after_svasti = text.split("SVASTI", 1)[1]
                # If CHAPTER I appears on the same page, stop there
                if m := re.search(r"\bCHAPTER\s*[-–]?\s*I\b", after_svasti):
                    raw_preamble = after_svasti[: m.start()]
                else:
                    raw_preamble = after_svasti
                # If the closing declaration is already present, the preamble is
                # complete on this page — no need to collect further pages
                if re.search(r"do hereby adopt and enact", raw_preamble):
                    break
            elif preamble_page is not None:
                # Collect continuation pages until CHAPTER I
                if m := re.search(r"\bCHAPTER\s*[-–]?\s*I\b", text):
                    raw_preamble += "\n" + text[: m.start()]
                    break
                raw_preamble += "\n" + text

        if not raw_preamble:
            raise ValueError("Could not locate preamble text in the PDF.")

        # Flatten to a single line so split patterns work across line breaks
        flat = re.sub(r"\s+", " ", raw_preamble).strip()

        # Split into paragraphs at known structural boundaries
        segments = [flat]
        for pattern in _PARA_SPLITS:
            new_segments: list[str] = []
            for seg in segments:
                parts = pattern.split(seg, maxsplit=1)
                new_segments.extend(parts)
            segments = new_segments

        paragraphs = [s.strip() for s in segments if s.strip()]
        return Preamble(
            text_paragraphs=paragraphs, original_doc_page_num=preamble_page
        )

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    def _cleaned_lines(
        self, pages: list[tuple[int, str]]
    ) -> list[tuple[int, str]]:
        """Return [(page_num, line), ...] with header/footer noise stripped."""
        result: list[tuple[int, str]] = []
        for page_num, text in pages:
            for raw in text.splitlines():
                s = raw.strip()
                if not s or _is_noise(s):
                    continue
                # PDF sometimes renders the digit "1" as lowercase "l" at the
                # start of article numbers (e.g. "l28." → "128.")
                s = re.sub(r"^l(\d+\.)(\s)", r"1\1\2", s)
                result.append((page_num, s))
        return result

    @staticmethod
    def _collect_page_footnotes(
        lines: list[tuple[int, str]]
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

    def _parse_chapters(
        self,
        pages: list[tuple[int, str]],
        marginalia: dict[str, str],
        page_footnotes: dict[int, list[Footnote]],
    ) -> list[Chapter]:
        lines = self._cleaned_lines(pages)

        # Find where chapters actually begin so the TOC doesn't interfere
        chapter_body_start = next(
            (i for i, (_, ln) in enumerate(lines) if _CHAPTER_RE.match(ln)), 0
        )

        # Truncate at the appendix marker, but only within the chapter body
        for cut, (_, ln) in enumerate(
            lines[chapter_body_start:], chapter_body_start
        ):
            if _BODY_END_RE.search(ln):
                lines = lines[:cut]
                break

        chapter_starts = [
            i for i, (_, ln) in enumerate(lines) if _CHAPTER_RE.match(ln)
        ]
        chapters: list[Chapter] = []
        for ci, start in enumerate(chapter_starts):
            end = (
                chapter_starts[ci + 1]
                if ci + 1 < len(chapter_starts)
                else len(lines)
            )
            chapter = self._parse_chapter_block(
                lines[start:end], marginalia, page_footnotes
            )
            if chapter:
                chapters.append(chapter)
        return chapters

    def _parse_chapter_block(
        self,
        lines: list[tuple[int, str]],
        marginalia: dict[str, str],
        page_footnotes: dict[int, list[Footnote]],
    ) -> Chapter | None:
        if not lines:
            return None
        page_num, chapter_line = lines[0]
        m = _CHAPTER_RE.match(chapter_line)
        if not m:
            return None

        numeral = m.group(1).upper()
        suffix = (m.group(2) or "").strip()
        # Convert roman numeral to zero-padded decimal, e.g. XVI+A → 016A
        chapter_number = _decimal_chapter_num(numeral, suffix)

        # Collect title lines: everything after the chapter header until first article
        title_lines: list[str] = []
        article_start = len(lines)
        for i in range(1, len(lines)):
            if _ARTICLE_RE.match(lines[i][1]):
                article_start = i
                break
            title_lines.append(lines[i][1])

        title = _AMEND_REF_RE.sub("", " ".join(title_lines)).strip()

        articles = self._parse_articles(
            lines[article_start:], marginalia, page_footnotes
        )
        return Chapter(
            number=chapter_number,
            title=title,
            articles=articles,
            original_doc_page_num=page_num,
        )

    def _parse_articles(
        self,
        lines: list[tuple[int, str]],
        marginalia: dict[str, str],
        page_footnotes: dict[int, list[Footnote]],
    ) -> list[Article]:
        article_starts = [
            i for i, (_, ln) in enumerate(lines) if _ARTICLE_RE.match(ln)
        ]
        articles: list[Article] = []
        for ai, start in enumerate(article_starts):
            end = (
                article_starts[ai + 1]
                if ai + 1 < len(article_starts)
                else len(lines)
            )
            art = self._parse_article_block(
                lines[start:end], marginalia, page_footnotes
            )
            if art:
                articles.append(art)
        return articles

    def _parse_article_block(
        self,
        lines: list[tuple[int, str]],
        marginalia: dict[str, str],
        page_footnotes: dict[int, list[Footnote]],
    ) -> Article | None:
        if not lines:
            return None
        page_num, first_line = lines[0]
        m = _ARTICLE_RE.match(first_line)
        if not m:
            return None

        art_number = m.group("num")

        # Resolve marginalia description for this article.
        title = marginalia.get(art_number) or None

        # Content of the first line starts after the matched article-number prefix
        first_content = first_line[m.end():].strip()

        # Collect content lines, skipping footnote lines (which belong to the
        # page pool rather than a specific article block).
        content_parts: list[str] = [first_content]
        for _, ln in lines[1:]:
            if not _FOOTNOTE_RE.match(ln):
                content_parts.append(ln)

        # Identify which amendment-reference markers appear in this article's
        # raw text (before stripping brackets) so we can assign the right
        # footnotes from the page pool.
        raw_with_markers = first_line + " " + " ".join(
            ln for _, ln in lines[1:] if not _FOOTNOTE_RE.match(ln)
        )
        used_markers = set(re.findall(r"(\d+)\[", raw_with_markers))

        # Pull matching footnotes from all pages spanned by this article.
        footnotes: list[Footnote] = []
        if used_markers:
            for pg in {pg for pg, _ in lines}:
                for fn in page_footnotes.get(pg, []):
                    if fn.marker in used_markers:
                        footnotes.append(fn)
            # Maintain stable ordering by marker number.
            footnotes.sort(key=lambda fn: int(fn.marker))

        # Build cleaned flat text — strip editorial amendment brackets
        raw = _AMEND_REF_RE.sub("", " ".join(content_parts))
        raw = re.sub(r"\s{2,}", " ", raw).strip()

        # Repealed article: entire content is just a Repealed marker
        if re.fullmatch(r"\[?Repealed\]?\.?", raw.strip(), re.IGNORECASE):
            return Article(
                number=art_number,
                description=title,
                text=None,
                repealed=True,
                footnotes=footnotes,
                original_doc_page_num=page_num,
            )

        clauses = _parse_clauses(raw)
        if clauses:
            first_clause_match = (
                _NUM_CLAUSE_RE.search(raw)
                if _NUM_CLAUSE_RE.search(raw)
                else _ALPHA_CLAUSE_RE.search(raw)
            )
            intro = (
                raw[: first_clause_match.start()].strip()
                if first_clause_match
                else None
            )
            return Article(
                number=art_number,
                description=title,
                text=intro or None,
                clauses=clauses,
                footnotes=footnotes,
                original_doc_page_num=page_num,
            )

        return Article(
            number=art_number,
            description=title,
            text=raw,
            footnotes=footnotes,
            original_doc_page_num=page_num,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> Constitution:
        pages = self._extract_pages()           # full text: metadata + preamble
        body_pages = self._extract_body_pages() # cropped: chapters + articles
        full_text = "\n".join(t for _, t in pages)
        meta = self._parse_metadata(full_text)
        preamble = self._parse_preamble(pages)
        marginalia = self._build_marginalia_map()
        # Footnotes on even pages have their number in the outer margin; use
        # full-page text so the number prefix is not cropped out.
        full_cleaned = self._cleaned_lines(pages)
        page_footnotes = self._collect_page_footnotes(full_cleaned)
        chapters = self._parse_chapters(body_pages, marginalia, page_footnotes)
        return Constitution(
            title=meta["title"],
            edition=meta["edition"],
            amended_up_to=meta["amended_up_to"],
            last_amendment=meta["last_amendment"],
            published_by=meta["published_by"],
            preamble=preamble,
            chapters=chapters,
        )

    def write(
        self,
        constitution: Constitution,
        output_dir: Path = _OUTPUT_DIR,
    ) -> Path:
        folder = (
            Path(output_dir) / f"lk-constitution-{constitution.amended_up_to}"
        )
        folder.mkdir(parents=True, exist_ok=True)

        # top-level.json — metadata + index (no embedded content)
        top_level = {
            "title": constitution.title,
            "edition": constitution.edition,
            "amended_up_to": constitution.amended_up_to,
            "last_amendment": constitution.last_amendment,
            "published_by": constitution.published_by,
            "chapters": [
                {
                    "number": ch.number,
                    "title": ch.title,
                    "file": f"chapter-{ch.number}.json",
                }
                for ch in constitution.chapters
            ],
            "schedules": [
                {
                    "number": sc.number,
                    "title": sc.title,
                    "file": f"schedule-{sc.number}.json",
                }
                for sc in constitution.schedules
            ],
        }
        _write_json(folder / "top-level.json", top_level)

        # preamble.json
        _write_json(folder / "preamble.json", asdict(constitution.preamble))

        # chapter-<NUMBER>.json — one per chapter
        for chapter in constitution.chapters:
            _write_json(
                folder / f"chapter-{chapter.number}.json", asdict(chapter)
            )
            # Remove any stale roman-numeral–named files from previous runs.
            for stale in folder.glob("chapter-[IVXLCivxlc]*.json"):
                stale.unlink(missing_ok=True)

        # schedule-<NUMBER>.json — one per schedule
        for schedule in constitution.schedules:
            _write_json(
                folder / f"schedule-{schedule.number}.json", asdict(schedule)
            )

        return folder


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _parse_clauses(text: str) -> list[Clause]:
    """Split article text into top-level Clause objects.

    Tries numeric (1),(2),... first; falls back to alpha (a),(b),... (a-h range).
    Returns [] when no clause markers are present.
    """
    if _NUM_CLAUSE_RE.search(text):
        pattern = _NUM_CLAUSE_RE
    elif _ALPHA_CLAUSE_RE.search(text):
        pattern = _ALPHA_CLAUSE_RE
    else:
        return []

    parts = pattern.split(text)
    # re.split with a capture group gives:
    # [before_first, label1, text1, label2, text2, ...]
    return [
        Clause(label=f"({parts[i]})", text=parts[i + 1].strip())
        for i in range(1, len(parts), 2)
        if i + 1 < len(parts)
    ]


def _parse_footnote_lines(lines: list[str]) -> list[Footnote]:
    result: list[Footnote] = []
    for ln in lines:
        if m := re.match(r"^(\d+)\s*[-\u2013]\s*(.+)$", ln):
            result.append(Footnote(marker=m.group(1), text=m.group(2).strip()))
    return result


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
