from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pdfplumber

from ..core import Constitution, Preamble

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
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> Constitution:
        pages = self._extract_pages()
        full_text = "\n".join(t for _, t in pages)
        meta = self._parse_metadata(full_text)
        preamble = self._parse_preamble(pages)
        return Constitution(
            title=meta["title"],
            edition=meta["edition"],
            amended_up_to=meta["amended_up_to"],
            last_amendment=meta["last_amendment"],
            published_by=meta["published_by"],
            preamble=preamble,
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
# Helper
# ------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


_PDF_PATH = Path("data/original_data/constitution.pdf")
_OUTPUT_DIR = Path("data/parsed")

# Patterns that identify page header / footer lines to strip
_NOISE_PATTERNS = [
    re.compile(r"^[xivXIV\s]+$", re.IGNORECASE),  # Roman numeral page labels
    re.compile(r"^\d+$"),  # bare page numbers
    re.compile(
        r"The Constitution of the Democratic Socialist Republic", re.IGNORECASE
    ),
]


def _is_noise(line: str) -> bool:
    return any(p.search(line) for p in _NOISE_PATTERNS)


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
