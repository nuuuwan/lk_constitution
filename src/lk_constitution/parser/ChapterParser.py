from __future__ import annotations

from ..core import Chapter, Footnote
from .ArticleParser import parse_articles
from .Constants import _AMEND_REF_RE, _ARTICLE_RE, _BODY_END_RE, _CHAPTER_RE
from .TextUtils import _cleaned_lines, _decimal_chapter_num


def parse_chapters(
    pages: list[tuple[int, str]],
    marginalia: dict[str, str],
    page_footnotes: dict[int, list[Footnote]],
) -> list[Chapter]:
    lines = _cleaned_lines(pages)
    chapter_body_start = next(
        (i for i, (_, ln) in enumerate(lines) if _CHAPTER_RE.match(ln)), 0
    )
    for cut, (_, ln) in enumerate(
        lines[chapter_body_start:], chapter_body_start
    ):
        if _BODY_END_RE.search(ln):
            lines = lines[:cut]
            break
    chapter_starts = [
        i for i, (_, ln) in enumerate(lines) if _CHAPTER_RE.match(ln)
    ]
    chapters: list[Chapter] = []
    for ci, start in enumerate(chapter_starts):
        end = (
            chapter_starts[ci + 1]
            if ci + 1 < len(chapter_starts)
            else len(lines)
        )
        chapter = _parse_chapter_block(
            lines[start:end], marginalia, page_footnotes
        )
        if chapter:
            chapters.append(chapter)
    return chapters


def _parse_chapter_block(
    lines: list[tuple[int, str]],
    marginalia: dict[str, str],
    page_footnotes: dict[int, list[Footnote]],
) -> Chapter | None:
    if not lines:
        return None
    page_num, chapter_line = lines[0]
    m = _CHAPTER_RE.match(chapter_line)
    if not m:
        return None
    numeral = m.group(1).upper()
    suffix = (m.group(2) or "").strip()
    chapter_number = _decimal_chapter_num(numeral, suffix)
    title_lines: list[str] = []
    article_start = len(lines)
    for i in range(1, len(lines)):
        if _ARTICLE_RE.match(lines[i][1]):
            article_start = i
            break
        title_lines.append(lines[i][1])
    title = _AMEND_REF_RE.sub("", " ".join(title_lines)).strip()
    articles = parse_articles(
        lines[article_start:], marginalia, page_footnotes
    )
    return Chapter(
        number=chapter_number,
        title=title,
        articles=articles,
        original_doc_page_num=page_num,
    )
