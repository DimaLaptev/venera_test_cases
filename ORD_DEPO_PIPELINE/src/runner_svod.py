"""Запуск сборки СВОД_поДЕПО для каталога периода."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from period_paths import parse_period_year_month
from runner import RunResult, resolve_period
from svod_prepare import prepare_svod_inputs


@dataclass(frozen=True)
class SvodRunPaths:
    svod_workbook: Path
    svod_dom_workbook: Path


def run_svod_period(
    pipeline_root: Path,
    reports_root: Path,
    *,
    period: str | None = None,
    period_dir: Path | None = None,
    skip_prepare: bool = False,
) -> RunResult:
    try:
        abs_period, name = resolve_period(
            reports_root, period=period, period_dir=period_dir
        )
    except ValueError as exc:
        return RunResult(
            ok=False,
            period_name=period or (period_dir.name if period_dir else ""),
            period_dir=Path("."),
            workbook=Path("."),
            exit_code=2,
            message=str(exc),
        )

    year, month = parse_period_year_month(name)
    if year is None or month is None:
        return RunResult(
            ok=False,
            period_name=name,
            period_dir=abs_period,
            workbook=Path("."),
            exit_code=2,
            message=f"Некорректное имя периода: {name!r}",
        )

    if not abs_period.is_dir():
        return RunResult(
            ok=False,
            period_name=name,
            period_dir=abs_period,
            workbook=Path("."),
            exit_code=2,
            message=(
                f"Каталог периода не найден: {abs_period} "
                f"(REPORTS_DEPO_DIRECTORY={reports_root})"
            ),
        )

    svod_dir = abs_period / "SVOD"
    workbook = svod_dir / "СВОД_поДЕПО.xlsx"
    prepare_log = ""

    if not skip_prepare:
        try:
            prep = prepare_svod_inputs(reports_root, name)
            prepare_log = "\n".join(prep.messages)
        except Exception as exc:
            return RunResult(
                ok=False,
                period_name=name,
                period_dir=abs_period,
                workbook=workbook,
                exit_code=2,
                message=f"Ошибка подготовки файлов SVOD для {name}: {exc}",
            )

    script = pipeline_root / "svod" / "scripts" / "run_pipeline.py"
    cmd = [
        sys.executable,
        str(script),
        "--pipeline-root",
        str(pipeline_root / "svod"),
        "--reports-root",
        str(reports_root),
        "--period",
        name,
        "--prior-from-svod",
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(pipeline_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined_out = "\n".join(
        x for x in (prepare_log, proc.stdout or "", proc.stderr or "") if x
    )
    if proc.returncode == 0:
        return RunResult(
            ok=True,
            period_name=name,
            period_dir=abs_period,
            workbook=workbook,
            exit_code=0,
            message=f"Готово: {workbook}",
            stdout=combined_out,
            stderr=proc.stderr or "",
        )

    detail = (proc.stderr or proc.stdout or "").strip() or f"код {proc.returncode}"
    return RunResult(
        ok=False,
        period_name=name,
        period_dir=abs_period,
        workbook=workbook,
        exit_code=proc.returncode,
        message=f"Ошибка сборки СВОД_поДЕПО для {name}: {detail}",
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
