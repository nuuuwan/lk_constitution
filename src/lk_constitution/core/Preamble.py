from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Preamble:
    text_paragraphs: list[str] = field(default_factory=list)
    original_doc_page_num: int | None = None
