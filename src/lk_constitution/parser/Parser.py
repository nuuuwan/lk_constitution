from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ..core import Constitution
from .ChapterParser import parse_chapters
from .Constants import _OUTPUT_DIR, _PDF_PATH
from .FootnoteUtils import collect_page_footnotes
from .Marginalia import build_marginalia_map
from .MetadataPreambleParser import parse_metadata, parse_preamble
from .PageExtractor import extract_body_pages, extract_full_pages
from .TextUtils import _cleaned_lines, _write_json


class Parser:
    def __init__(self, pdf_path: Path = _PDF_PATH):
        self.pdf_path = Path(pdf_path)
        self._pages: list[tuple[int, str]] | None = None
        self._body_pages: list[tuple[int, str]] | None = None

    def _get_pages(self) -> list[tuple[int, str]]:
        if self._pages is None:
            self._pages = extract_full_pages(self.pdf_path)
        return self._pages

    def _get_body_pages(self) -> list[tuple[int, str]]:
        if self._body_pages is None:
            self._body_pages = extract_body_pages(self.pdf_path)
        return self._body_pages

    def parse(self) -> Constitution:
        pages = self._get_pages()
        body_pages = self._get_body_pages()
        full_text = "\n".join(t for _, t in pages)
        meta = parse_metadata(full_text)
        preamble = parse_preamble(pages)
        marginalia = build_marginalia_map(self.pdf_path)
        full_cleaned = _cleaned_lines(pages)
        page_footnotes = collect_page_footnotes(full_cleaned)
        chapters = parse_chapters(body_pages, marginalia, page_footnotes)
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
        _write_json(folder / "preamble.json", asdict(constitution.preamble))
        for chapter in constitution.chapters:
            _write_json(
                folder / f"chapter-{chapter.number}.json", asdict(chapter)
            )
            for stale in folder.glob("chapter-[IVXLCivxlc]*.json"):
                stale.unlink(missing_ok=True)
        for schedule in constitution.schedules:
            _write_json(
                folder / f"schedule-{schedule.number}.json",
                asdict(schedule),
            )
        return folder
