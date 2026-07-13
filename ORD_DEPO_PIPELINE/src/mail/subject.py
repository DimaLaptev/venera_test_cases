"""Парсинг темы письма: Ord <2026_05>."""

from __future__ import annotations

import re

_SUBJECT_RE = re.compile(
    r"^\s*Ord\s*<\s*(\d{4}_\d{1,2})\s*>\s*$",
    re.IGNORECASE,
)


def parse_ord_subject(subject: str | None) -> str | None:
    """Вернуть имя периода (например 2026_05) или None."""
    if not subject:
        return None
    # Убрать Re:/Fwd: префиксы
    cleaned = subject.strip()
    while True:
        lowered = cleaned.lower()
        if lowered.startswith("re:") or lowered.startswith("fw:") or lowered.startswith("fwd:"):
            cleaned = cleaned.split(":", 1)[1].strip()
            continue
        break
    m = _SUBJECT_RE.match(cleaned)
    if not m:
        return None
    return m.group(1)
