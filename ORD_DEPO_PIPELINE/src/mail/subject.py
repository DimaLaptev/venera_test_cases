"""Парсинг темы письма: Ord <2026_05> / Svod <2026_05> [dir]."""

from __future__ import annotations

import re
from dataclasses import dataclass

_ORD_SUBJECT_RE = re.compile(
    r"^\s*Ord\s*<\s*(\d{4}_\d{1,2})\s*>\s*$",
    re.IGNORECASE,
)
_SVOD_SUBJECT_RE = re.compile(
    r"^\s*Svod\s*<\s*(\d{4}_\d{1,2})\s*>\s*(?:(dir)\s*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SvodSubject:
    """Тема Svod: период и опционально dir — файлы _SVOD/REGION без API."""

    period: str
    region_from_dir: bool = False


def _strip_reply_prefixes(subject: str) -> str:
    cleaned = subject.strip()
    while True:
        lowered = cleaned.lower()
        if lowered.startswith("re:") or lowered.startswith("fw:") or lowered.startswith("fwd:"):
            cleaned = cleaned.split(":", 1)[1].strip()
            continue
        break
    return cleaned


def parse_ord_subject(subject: str | None) -> str | None:
    """Вернуть имя периода (например 2026_05) или None."""
    if not subject:
        return None
    m = _ORD_SUBJECT_RE.match(_strip_reply_prefixes(subject))
    if not m:
        return None
    return m.group(1)


def parse_svod_subject(subject: str | None) -> SvodSubject | None:
    """Разобрать тему Svod <YYYY_MM> [dir] или None."""
    if not subject:
        return None
    m = _SVOD_SUBJECT_RE.match(_strip_reply_prefixes(subject))
    if not m:
        return None
    return SvodSubject(
        period=m.group(1),
        region_from_dir=bool(m.group(2)),
    )
