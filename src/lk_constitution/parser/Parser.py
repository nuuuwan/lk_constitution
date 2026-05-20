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
_CHAPTER_RE = re.compile(
    r"^(?:\d+\[)?CHAPTER\s+([IVXLC]+)\s*([A-Z])?\s*\]?$"
)
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

    # ------------------------------------------------------------------
    # Page extraction
    # ------------------------------------------------------------------

    def _extract_pages(self) -> list[tuple[int, str]]:
        """Return [(pdf_page_number, text), …] for every page in the PDF."""
        if self._pages is None:
            with pdfplumber.open(self.pdf_path) as pdf:
                self._pages = [
                    (p.page_number, p.extract_text() or "") for p in pdf.pages
                ]
        return self._pages

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

    def _cleaned_lines(self, pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
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

    def _parse_chapters(self, pages: list[tuple[int, str]]) -> list[Chapter]:
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
            chapter = self._parse_chapter_block(lines[start:end])
            if chapter:
                chapters.append(chapter)
        return chapters

    def _parse_chapter_block(
        self, lines: list[tuple[int, str]]
    ) -> Chapter | None:
        if not lines:
            return None
        page_num, chapter_line = lines[0]
        m = _CHAPTER_RE.match(chapter_line)
        if not m:
            return None

        numeral = m.group(1).upper()
        suffix = (m.group(2) or "").strip()
        chapter_number = numeral + suffix  # e.g. "I", "VIIA", "XIXB"

        # Collect title lines: everything after the chapter header until first article
        title_lines: list[str] = []
        article_start = len(lines)
        for i in range(1, len(lines)):
            if _ARTICLE_RE.match(lines[i][1]):
                article_start = i
                break
            title_lines.append(lines[i][1])

        title = _AMEND_REF_RE.sub("", " ".join(title_lines)).strip()

        articles = self._parse_articles(lines[article_start:])
        return Chapter(
            number=chapter_number,
            title=title,
            articles=articles,
            original_doc_page_num=page_num,
        )

    def _parse_articles(
        self, lines: list[tuple[int, str]]
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
            art = self._parse_article_block(lines[start:end])
            if art:
                articles.append(art)
        return articles

    def _parse_article_block(
        self, lines: list[tuple[int, str]]
    ) -> Article | None:
        if not lines:
            return None
        page_num, first_line = lines[0]
        m = _ARTICLE_RE.match(first_line)
        if not m:
            return None

        art_number = m.group("num")

        # Content of the first line starts after the matched article-number prefix
        first_content = first_line[m.end():].strip()

        # Separate footnote lines from content lines (remaining lines after first)
        content_parts: list[str] = [first_content]
        raw_footnotes: list[str] = []
        for _, ln in lines[1:]:
            if _FOOTNOTE_RE.match(ln):
                raw_footnotes.append(ln)
            else:
                content_parts.append(ln)

        # Build cleaned flat text — strip editorial amendment brackets
        raw = _AMEND_REF_RE.sub("", " ".join(content_parts))
        raw = re.sub(r"\s{2,}", " ", raw).strip()

        footnotes = _parse_footnote_lines(raw_footnotes)

        # Repealed article: entire content is just a Repealed marker
        if re.fullmatch(r"\[?Repealed\]?\.?", raw.strip(), re.IGNORECASE):
            return Article(
                number=art_number,
                title=None,
                text=None,
                repealed=True,
                footnotes=footnotes,
                original_doc_page_num=page_num,
            )

        clauses = _parse_clauses(raw)
        if clauses:
            # If there's text before the first clause marker, put it in the intro
            # by checking what's before the first (1)/(a) in the raw text
            first_clause_match = (
                _NUM_CLAUSE_RE.search(raw)
                if _NUM_CLAUSE_RE.search(raw)
                else _ALPHA_CLAUSE_RE.search(raw)
            )
            intro = raw[: first_clause_match.start()].strip() if first_clause_match else None
            return Article(
                number=art_number,
                title=None,
                text=intro or None,
                clauses=clauses,
                footnotes=footnotes,
                original_doc_page_num=page_num,
            )

        return Article(
            number=art_number,
            title=None,
            text=raw,
            footnotes=footnotes,
            original_doc_page_num=page_num,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> Constitution:
        pages = self._extract_pages()
        full_text = "\n".join(t for _, t in pages)
        meta = self._parse_metadata(full_text)
        preamble = self._parse_preamble(pages)
        chapters = self._parse_chapters(pages)
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
