from __future__ import annotations

from dataclasses import dataclass, field

from .Chapter import Chapter
from .Preamble import Preamble
from .Schedule import Schedule


@dataclass
class Constitution:
    title: str
    edition: str
    amended_up_to: str
    last_amendment: str
    published_by: str
    preamble: Preamble
    chapters: list[Chapter] = field(default_factory=list)
    schedules: list[Schedule] = field(default_factory=list)
