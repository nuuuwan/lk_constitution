from __future__ import annotations

import re

from ..core import Article, Footnote
from .Constants import (
    _ALPHA_CLAUSE_RE,
    _AMEND_REF_RE,
    _ARTICLE_RE,
    _FOOTNOTE_RE,
    _NUM_CLAUSE_RE,
)
from .FootnoteUtils import match_article_footnotes
from .TextUtils import _parse_clauses


def parse_articles(
    lines: list[tuple[int, str]],
    marginalia: dict[str, str],
    page_footnotes: dict[int, list[Footnote]],
) -> list[Article]:
    article_starts = [
        i for i, (_, ln) in enumerate(lines) if _ARTICLE_RE.match(ln)
    ]
    articles: list[Article] = []
    for ai, start in enumerate(article_starts):
        end = (
            article_starts[ai + 1]
            if ai + 1 < len(article_starts)
            else len(lines)
        )
        art = _parse_article_block(
            lines[start:end], marginalia, page_footnotes
        )
        if art:
            articles.append(art)
    return articles


def _parse_article_block(
    lines: list[tuple[int, str]],
    marginalia: dict[str, str],
    page_footnotes: dict[int, list[Footnote]],
) -> Article | None:
    if not lines:
        return None
    page_num, first_line = lines[0]
    m = _ARTICLE_RE.match(first_line)
    if not m:
        return None
    art_number = m.group("num")
    description = marginalia.get(art_number) or None
    first_content = first_line[m.end() :].strip()
    content_parts: list[str] = [first_content]
    for _, ln in lines[1:]:
        if not _FOOTNOTE_RE.match(ln):
            content_parts.append(ln)
    footnotes = match_article_footnotes(lines, page_footnotes)
    raw = _AMEND_REF_RE.sub("", " ".join(content_parts))
    raw = re.sub(r"\s{2,}", " ", raw).strip()
    if re.fullmatch(r"\[?Repealed\]?\.?", raw.strip(), re.IGNORECASE):
        return Article(
            number=art_number,
            description=description,
            text=None,
            repealed=True,
            footnotes=footnotes,
            original_doc_page_num=page_num,
        )
    clauses = _parse_clauses(raw)
    if clauses:
        first_match = (
            _NUM_CLAUSE_RE.search(raw)
            if _NUM_CLAUSE_RE.search(raw)
            else _ALPHA_CLAUSE_RE.search(raw)
        )
        intro = raw[: first_match.start()].strip() if first_match else None
        return Article(
            number=art_number,
            description=description,
            text=intro or None,
            clauses=clauses,
            footnotes=footnotes,
            original_doc_page_num=page_num,
        )
    return Article(
        number=art_number,
        description=description,
        text=raw,
        footnotes=footnotes,
        original_doc_page_num=page_num,
    )
