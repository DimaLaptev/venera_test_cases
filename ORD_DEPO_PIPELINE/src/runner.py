"""Запуск сборки Ord_Quantity для каталога периода."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from period_paths import parse_period_year_month, resolve_period_dir


@dataclass(frozen=True)
class RunResult:
    ok: bool
    period_name: str
    period_dir: Path
    workbook: Path
    exit_code: int
    message: str
    stdout: str = ""
    stderr: str = ""


def format_failure_email_text(result: RunResult) -> str:
    """Полный текст ошибки для SMTP: message + stdout + stderr."""
    parts = [result.message.strip()]
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if stdout and stdout not in result.message:
        parts.append("--- stdout ---\n" + stdout)
    if stderr and stderr not in result.message and stderr != stdout:
        parts.append("--- stderr ---\n" + stderr)
    return "\n\n".join(parts)


def resolve_period(
    reports_root: Path,
    *,
    period: str | None = None,
    period_dir: Path | None = None,
) -> tuple[Path, str]:
    """Вернуть абсолютный каталог периода и его имя (2026_05)."""
    if period_dir is not None:
        p = Path(period_dir)
        if not p.is_absolute():
            p = (reports_root / p).resolve()
        else:
            p = p.resolve()
        return p, p.name
    if not period:
        raise ValueError("Укажите period или period_dir")
    name = period.strip()
    year, month = parse_period_year_month(name)
    if year is None or month is None:
        raise ValueError(f"Некорректное имя периода: {period!r} (ожидается YYYY_MM)")
    return (reports_root / name).resolve(), name


def run_ord_period(
    pipeline_root: Path,
    reports_root: Path,
    *,
    period: str | None = None,
    period_dir: Path | None = None,
    skip_dks: bool = False,
    skip_reps: bool = False,
    skip_svod: bool = False,
    skip_ord: bool = False,
    init_workbook: bool = False,
    ensure_reference_sheets: bool = False,
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

    pp = resolve_period_dir(abs_period, pipeline_root)
    if not abs_period.is_dir():
        return RunResult(
            ok=False,
            period_name=name,
            period_dir=abs_period,
            workbook=pp.workbook,
            exit_code=2,
            message=(
                f"Каталог периода не найден: {abs_period} "
                f"(REPORTS_DEPO_DIRECTORY={reports_root})"
            ),
        )

    if not init_workbook and not pp.workbook.is_file():
        return RunResult(
            ok=False,
            period_name=name,
            period_dir=abs_period,
            workbook=pp.workbook,
            exit_code=2,
            message=(
                f"Ожидается файл-основа {pp.workbook.name} в каталоге периода "
                f"{abs_period}"
            ),
        )

    script = pipeline_root / "scripts" / "fill_ord_period.py"
    cmd = [
        sys.executable,
        str(script),
        "--period-dir",
        str(abs_period),
    ]
    if init_workbook:
        cmd.append("--init-workbook")
    if ensure_reference_sheets:
        cmd.append("--ensure-reference-sheets")
    if skip_dks:
        cmd.append("--skip-dks")
    if skip_reps:
        cmd.append("--skip-reps")
    if skip_svod:
        cmd.append("--skip-svod")
    if skip_ord:
        cmd.append("--skip-ord")

    proc = subprocess.run(
        cmd,
        cwd=str(pipeline_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0:
        return RunResult(
            ok=True,
            period_name=name,
            period_dir=abs_period,
            workbook=pp.workbook,
            exit_code=0,
            message=f"Готово: {pp.workbook}",
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )

    detail = (proc.stderr or proc.stdout or "").strip() or f"код {proc.returncode}"
    return RunResult(
        ok=False,
        period_name=name,
        period_dir=abs_period,
        workbook=pp.workbook,
        exit_code=proc.returncode,
        message=f"Ошибка сборки Ord_Quantity для {name}: {detail}",
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
