from __future__ import annotations

import re

from ..core import Schedule, ScheduleItem
from ..core.Schedule import ContentType
from .Constants import (
    _ORDINAL_TO_SCHEDULE_NUM,
    _SCHED_ARTICLE_RE,
    _SCHEDULE_RE,
)
from .LegislativeListParser import parse_legislative_lists
from .TextUtils import _cleaned_lines

_IMAGE = {2, 3}
_OATH = {4, 7}
_TEXT = {6}
_FN_RE = re.compile(
    r"^\d+\s*[-\u2013]\s*(?:Substituted|Inserted|Repealed|Added|Amended"
    r"|Omitted|Deleted|Replaced)",
    re.IGNORECASE,
)


def parse_schedules(pages: list[tuple[int, str]]) -> list[Schedule]:
    lines = _cleaned_lines(pages)
    starts = [i for i, (_, ln) in enumerate(lines) if _SCHEDULE_RE.match(ln)]
    result = []
    for si, start in enumerate(starts):
        end = starts[si + 1] if si + 1 < len(starts) else len(lines)
        s = _block(lines[start:end])
        if s:
            result.append(s)
    return result


def _block(lines: list[tuple[int, str]]) -> Schedule | None:
    if not lines:
        return None
    page_num, hdr = lines[0]
    m = _SCHEDULE_RE.match(hdr)
    if not m:
        return None
    num = _ORDINAL_TO_SCHEDULE_NUM[m.group(1).upper()]
    pos, referred_by = 1, None
    if pos < len(lines) and (am := _SCHED_ARTICLE_RE.match(lines[pos][1])):
        referred_by = _ca(am.group(1))
        pos += 1
    title, pos = _title(lines, pos)
    body = lines[pos:]
    kw = dict(referred_by_article=referred_by, original_doc_page_num=page_num)
    if num in _IMAGE:
        return Schedule(num, title, ContentType.IMAGE, **kw)
    if num in _OATH:
        return Schedule(num, title, ContentType.OATH, text=_txt(body), **kw)
    if num in _TEXT:
        return Schedule(num, title, ContentType.TEXT, text=_txt(body), **kw)
    if num == 9:
        return Schedule(
            num, title, ContentType.LEGISLATIVE_LIST,
            lists=parse_legislative_lists(body), **kw
        )
    return Schedule(num, title, ContentType.LIST, items=_items(body), **kw)


def _ca(s: str) -> str:
    return re.sub(r"\d+\[|\]", "", s).strip()


def _title(lines: list[tuple[int, str]], pos: int) -> tuple[str, int]:
    if pos < len(lines):
        ln = lines[pos][1]
        if not (re.match(r'[\d"]', ln) or
                re.match(r"LIST\s+", ln, re.I) or
                re.search(r"\d\s+Member", ln)):
            return _ca(ln), pos + 1
    return "", pos


def _txt(lines: list[tuple[int, str]]) -> str:
    return re.sub(r"\s+", " ",
                  " ".join(ln for _, ln in lines
                           if not _FN_RE.match(ln))).strip()


def _items(lines: list[tuple[int, str]]) -> list[ScheduleItem]:
    items, n = [], 0
    for _, ln in lines:
        if _FN_RE.match(ln):
            continue
        clean = _ca(ln)
        if not clean:
            continue
        if mm := re.match(r"^\d+\s*\[(\d+)\s+(.+?)\]\s*$", ln):
            n, v = int(mm.group(1)), mm.group(2).strip()
        elif mm := re.match(r"^(\d+)\.?\s+(.+)", clean):
            n, v = int(mm.group(1)), mm.group(2).strip()
        else:
            n += 1
            v = clean
        items.append(ScheduleItem(n, v))
    return items
