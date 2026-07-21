"""Парсинг темы письма: Ord <2026_05> / Svod <2026_05>."""

from __future__ import annotations

import re

_ORD_SUBJECT_RE = re.compile(
    r"^\s*Ord\s*<\s*(\d{4}_\d{1,2})\s*>\s*$",
    re.IGNORECASE,
)
_SVOD_SUBJECT_RE = re.compile(
    r"^\s*Svod\s*<\s*(\d{4}_\d{1,2})\s*>\s*$",
    re.IGNORECASE,
)


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


def parse_svod_subject(subject: str | None) -> str | None:
    """Вернуть имя периода из темы Svod <YYYY_MM> или None."""
    if not subject:
        return None
    m = _SVOD_SUBJECT_RE.match(_strip_reply_prefixes(subject))
    if not m:
        return None
    return m.group(1)
