"""Тесты cooldown повторного запуска по письму."""

from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))

from mail.job_cooldown import (
    JOB_COOLDOWN_SEC,
    record_job_start,
    remaining_cooldown_sec,
)


def test_first_job_not_on_cooldown() -> None:
    last: dict[str, float] = {}
    assert remaining_cooldown_sec(last, "ord:2026_05", now=1_000.0) is None


def test_same_job_skipped_within_120_minutes() -> None:
    last: dict[str, float] = {}
    record_job_start(last, "ord:2026_05", now=1_000.0)
    left = remaining_cooldown_sec(last, "ord:2026_05", now=1_000.0 + 119 * 60)
    assert left is not None
    assert abs(left - 60) < 0.01


def test_same_job_allowed_after_120_minutes() -> None:
    last: dict[str, float] = {}
    record_job_start(last, "ord:2026_05", now=1_000.0)
    assert remaining_cooldown_sec(last, "ord:2026_05", now=1_000.0 + JOB_COOLDOWN_SEC) is None
    assert remaining_cooldown_sec(last, "ord:2026_05", now=1_000.0 + JOB_COOLDOWN_SEC + 1) is None


def test_svod_and_ord_same_period_are_independent() -> None:
    last: dict[str, float] = {}
    record_job_start(last, "ord:2026_05", now=1_000.0)
    assert remaining_cooldown_sec(last, "svod:2026_05", now=1_000.0) is None


def test_other_month_not_blocked() -> None:
    last: dict[str, float] = {}
    record_job_start(last, "ord:2026_05", now=1_000.0)
    assert remaining_cooldown_sec(last, "ord:2026_06", now=1_000.0) is None
