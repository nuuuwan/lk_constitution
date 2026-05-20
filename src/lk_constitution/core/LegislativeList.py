from __future__ import annotations

from dataclasses import dataclass, field

from .LegislativeListItem import LegislativeListItem


@dataclass
class LegislativeList:
    list_id: str
    name: str
    items: list[LegislativeListItem] = field(default_factory=list)
