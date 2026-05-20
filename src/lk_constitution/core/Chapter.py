from __future__ import annotations

from dataclasses import dataclass, field

from .Article import Article


@dataclass
class Chapter:
    number: str
    title: str
    articles: list[Article] = field(default_factory=list)
    original_doc_page_num: int | None = None
