"""Cooldown повторного запуска сборки по письму (ord/svod + период)."""

from __future__ import annotations

import time

# Повторное письмо с тем же видом и периодом не запускает сборку 120 минут
# от предыдущего письма, которое реально стартовало сборку.
JOB_COOLDOWN_SEC = 120 * 60


def remaining_cooldown_sec(
    last_started: dict[str, float],
    job_key: str,
    *,
    now: float | None = None,
    cooldown_sec: int = JOB_COOLDOWN_SEC,
) -> float | None:
    """Секунды до конца окна, либо None если сборку можно запускать."""
    prev = last_started.get(job_key)
    if prev is None:
        return None
    current = time.time() if now is None else now
    left = cooldown_sec - (current - prev)
    if left <= 0:
        return None
    return left


def record_job_start(
    last_started: dict[str, float],
    job_key: str,
    *,
    now: float | None = None,
) -> None:
    last_started[job_key] = time.time() if now is None else now
