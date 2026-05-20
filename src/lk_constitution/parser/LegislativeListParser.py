from __future__ import annotations

import re

from ..core import LegislativeList, LegislativeListItem

_LIST_HEADER_RE = re.compile(
    r"^LIST\s+(I{1,3}|IV|V|VI|VII|VIII|IX|X)\s*$", re.IGNORECASE
)
_LIST_NAME_RE = re.compile(r"^\((.+)\)$")
_ITEM_RE = re.compile(r"^(\d+)\.\s+(.+)")
_DASH_RE = re.compile(r"[\u2013\u2014]")


def parse_legislative_lists(
    lines: list[tuple[int, str]],
) -> list[LegislativeList]:
    starts = [
        i for i, (_, ln) in enumerate(lines) if _LIST_HEADER_RE.match(ln)
    ]
    if not starts:
        return []
    result = []
    for si, start in enumerate(starts):
        end = starts[si + 1] if si + 1 < len(starts) else len(lines)
        ll = _parse_single(lines[start:end])
        if ll:
            result.append(ll)
    return result


def _parse_single(lines: list[tuple[int, str]]) -> LegislativeList | None:
    if not lines:
        return None
    _, hdr = lines[0]
    m = _LIST_HEADER_RE.match(hdr)
    if not m:
        return None
    list_id = m.group(1).upper()
    name, start = "", 1
    if len(lines) > 1 and (nm := _LIST_NAME_RE.match(lines[1][1])):
        name = nm.group(1)
        start = 2
    items = _numbered(lines[start:]) or _by_topic(lines[start:])
    return LegislativeList(list_id=list_id, name=name, items=items)


def _numbered(lines: list[tuple[int, str]]) -> list[LegislativeListItem]:
    items: list[LegislativeListItem] = []
    cur_n: int | None = None
    cur_s, cur_d = "", []

    for _, ln in lines:
        if m := _ITEM_RE.match(ln):
            if cur_n is not None:
                items.append(LegislativeListItem(
                    cur_n, cur_s, re.sub(r"\s+", " ", " ".join(cur_d)).strip()
                ))
            cur_n = int(m.group(1))
            rest = m.group(2).strip()
            parts = _DASH_RE.split(rest, 1)
            cur_s = re.sub(r"\s*\.\s*$", "", parts[0]).strip()
            cur_d = [parts[1].strip()] if len(parts) > 1 and parts[1].strip() else []
        elif cur_n is not None:
            cur_d.append(ln)
    if cur_n is not None:
        items.append(LegislativeListItem(
            cur_n, cur_s, re.sub(r"\s+", " ", " ".join(cur_d)).strip()
        ))
    return items


def _by_topic(lines: list[tuple[int, str]]) -> list[LegislativeListItem]:
    """Parse un-numbered items (e.g. List II) by detecting topic headings."""
    items: list[LegislativeListItem] = []
    cur_n, cur_s, cur_d = 0, "", []

    for _, ln in lines:
        is_topic = (
            bool(ln) and ln[0].isupper()
            and not ln.startswith(("(", "This", "–", "-"))
            and not re.match(r"^\d", ln)
        )
        if is_topic and cur_s:
            items.append(LegislativeListItem(
                cur_n, cur_s, re.sub(r"\s+", " ", " ".join(cur_d)).strip()
            ))
            cur_d = []
        if is_topic:
            cur_n += 1
            cur_s = ln
        else:
            cur_d.append(ln)
    if cur_s:
        items.append(LegislativeListItem(
            cur_n, cur_s, re.sub(r"\s+", " ", " ".join(cur_d)).strip()
        ))
    return items
