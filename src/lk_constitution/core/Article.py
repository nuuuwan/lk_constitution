from __future__ import annotations

from dataclasses import dataclass, field

from .Clause import Clause
from .Footnote import Footnote


@dataclass
class Article:
    number: str
    description: str | None
    text: str | None
    clauses: list[Clause] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    repealed: bool = False
    original_doc_page_num: int | None = None
