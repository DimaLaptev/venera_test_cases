"""Тесты парсера темы Ord <YYYY_MM> / Svod <YYYY_MM>."""

from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from mail.subject import parse_ord_subject, parse_svod_subject


def test_parse_ord_subject_ok() -> None:
    assert parse_ord_subject("Ord <2026_05>") == "2026_05"
    assert parse_ord_subject("ord <2026_1>") == "2026_1"
    assert parse_ord_subject("  ORD <2026_01>  ") == "2026_01"


def test_parse_ord_subject_with_reply_prefix() -> None:
    assert parse_ord_subject("Re: Ord <2026_05>") == "2026_05"
    assert parse_ord_subject("Fwd: Ord <2026_05>") == "2026_05"


def test_parse_ord_subject_reject() -> None:
    assert parse_ord_subject("Hello") is None
    assert parse_ord_subject("Ord 2026_05") is None
    assert parse_ord_subject("") is None
    assert parse_ord_subject(None) is None
    assert parse_ord_subject("Svod <2026_05>") is None


def test_parse_svod_subject_ok() -> None:
    assert parse_svod_subject("Svod <2026_05>") == "2026_05"
    assert parse_svod_subject("svod <2026_1>") == "2026_1"
    assert parse_svod_subject("  SVOD <2026_01>  ") == "2026_01"


def test_parse_svod_subject_with_reply_prefix() -> None:
    assert parse_svod_subject("Re: Svod <2026_05>") == "2026_05"
    assert parse_svod_subject("Fwd: Svod <2026_05>") == "2026_05"


def test_parse_svod_subject_reject() -> None:
    assert parse_svod_subject("Hello") is None
    assert parse_svod_subject("Svod 2026_05") is None
    assert parse_svod_subject("Ord <2026_05>") is None
    assert parse_svod_subject("") is None
    assert parse_svod_subject(None) is None
