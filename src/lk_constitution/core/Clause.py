from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Clause:
    label: str
    text: str
    sub_clauses: list[Clause] = field(default_factory=list)
