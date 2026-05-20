from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .LegislativeList import LegislativeList
from .ScheduleItem import ScheduleItem


class ContentType(str, Enum):
    LIST = "list"
    IMAGE = "image"
    TEXT_AND_IMAGE = "text_and_image"
    OATH = "oath"
    LEGISLATIVE_LIST = "legislative_list"
    TEXT = "text"


@dataclass
class Schedule:
    number: int
    title: str
    content_type: ContentType
    referred_by_article: str | None = None
    description: str | None = None
    text: str | None = None
    items: list[ScheduleItem] = field(default_factory=list)
    lists: list[LegislativeList] = field(default_factory=list)
    original_doc_page_num: int | None = None
