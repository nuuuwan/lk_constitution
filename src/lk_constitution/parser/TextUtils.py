from __future__ import annotations

import json
import re
from pathlib import Path

from ..core import Clause, Footnote
from .Constants import (
    _ALPHA_CLAUSE_RE,
    _NOISE_PATTERNS,
    _NUM_CLAUSE_RE,
    _ROMAN_VALUES,
)


def _roman_to_int(s: str) -> int:
    result, prev = 0, 0
    for ch in reversed(s.upper()):
        val = _ROMAN_VALUES[ch]
        result += val if val >= prev else -val
        prev = val
    return result


def _decimal_chapter_num(roman: str, suffix: str) -> str:
    """Convert e.g. roman='XVI', suffix='A' → '016A'."""
    return f"{_roman_to_int(roman):03d}{suffix}"


def _is_noise(line: str) -> bool:
    return any(p.search(line) for p in _NOISE_PATTERNS)


def _cleaned_lines(
    pages: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Return [(page_num, line), ...] with header/footer noise stripped."""
    result: list[tuple[int, str]] = []
    for page_num, text in pages:
        for raw in text.splitlines():
            s = raw.strip()
            if not s or _is_noise(s):
                continue
            # PDF sometimes renders "1" as "l" at the start of article numbers
            s = re.sub(r"^l(\d+\.)(\s)", r"1\1\2", s)
            result.append((page_num, s))
    return result


def _parse_clauses(text: str) -> list[Clause]:
    """Split article text into top-level Clause objects."""
    if _NUM_CLAUSE_RE.search(text):
        pattern = _NUM_CLAUSE_RE
    elif _ALPHA_CLAUSE_RE.search(text):
        pattern = _ALPHA_CLAUSE_RE
    else:
        return []
    parts = pattern.split(text)
    return [
        Clause(label=f"({parts[i]})", text=parts[i + 1].strip())
        for i in range(1, len(parts), 2)
        if i + 1 < len(parts)
    ]


def _parse_footnote_lines(lines: list[str]) -> list[Footnote]:
    result: list[Footnote] = []
    for ln in lines:
        if m := re.match(r"^(\d+)\s*[-\u2013]\s*(.+)$", ln):
            result.append(Footnote(marker=m.group(1), text=m.group(2).strip()))
    return result


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
