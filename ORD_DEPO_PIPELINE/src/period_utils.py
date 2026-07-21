"""Пути и даты периода SVOD под REPORTS_DEPO_DIRECTORY."""

from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_PERIOD_RE = re.compile(r"^(\d{4})_(\d{1,2})$")


@dataclass(frozen=True)
class SvodPeriodPaths:
    period_name: str
    prev_period_name: str
    period_dir: Path
    svod_dir: Path
    gpb: Path
    rsd_msg: Path
    rsd_exl: Path
    region: Path
    vtbsd: Path
    staging: Path
    sprav_workbook: Path
    svod_workbook: Path
    svod_dom_workbook: Path
    depo_ia: Path
    depo_dom: Path
    gpb_r_src: Path
    rsd_r_src: Path
    rsd_rep_src: Path
    report_date: str
    year: int
    month: int


def parse_period_year_month(period_name: str) -> tuple[int | None, int | None]:
    m = _PERIOD_RE.match(period_name.strip())
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def previous_period_name(period_name: str) -> str:
    """Предыдущий месяц; стиль нуля месяца как у входа (2026_05→2026_04, 2026_5→2026_4)."""
    year, month = parse_period_year_month(period_name)
    if year is None or month is None:
        raise ValueError(f"Некорректное имя периода: {period_name!r}")
    if month == 1:
        py, pm = year - 1, 12
    else:
        py, pm = year, month - 1
    suffix = period_name.split("_", 1)[1]
    if len(suffix) >= 2 and suffix[0] == "0":
        return f"{py}_{pm:02d}"
    return f"{py}_{pm}"


def period_last_day(period_name: str) -> date:
    year, month = parse_period_year_month(period_name)
    if year is None or month is None:
        raise ValueError(f"Некорректное имя периода: {period_name!r}")
    last = monthrange(year, month)[1]
    return date(year, month, last)


def report_date_for_period(period_name: str) -> str:
    """Последний день месяца периода как ДД.ММ.ГГГГ."""
    return period_last_day(period_name).strftime("%d.%m.%Y")


def period_date_tokens(period_name: str) -> tuple[str, str]:
    """(YYYYMMDD, YYMMDD) для фильтра имён файлов."""
    d = period_last_day(period_name)
    return d.strftime("%Y%m%d"), d.strftime("%y%m%d")


def filename_matches_period_end(filename: str, period_name: str) -> bool:
    yyyymmdd, yymmdd = period_date_tokens(period_name)
    name = Path(filename).name
    return yyyymmdd in name or yymmdd in name


def resolve_svod_period_paths(reports_root: Path, period_name: str) -> SvodPeriodPaths:
    year, month = parse_period_year_month(period_name)
    if year is None or month is None:
        raise ValueError(f"Некорректное имя периода: {period_name!r}")
    prev = previous_period_name(period_name)
    period_dir = (reports_root / period_name).resolve()
    prev_dir = (reports_root / prev).resolve()
    svod_dir = period_dir / "SVOD"
    prev_svod = prev_dir / "SVOD"
    return SvodPeriodPaths(
        period_name=period_name,
        prev_period_name=prev,
        period_dir=period_dir,
        svod_dir=svod_dir,
        gpb=svod_dir / "GPB",
        rsd_msg=svod_dir / "RSD_MSG",
        rsd_exl=svod_dir / "RSD_EXL",
        region=svod_dir / "REGION",
        vtbsd=svod_dir / "VTBSD",
        staging=svod_dir / "_staging",
        sprav_workbook=reports_root / "depo_validation" / "Справочник.xlsx",
        svod_workbook=svod_dir / "СВОД_поДЕПО.xlsx",
        svod_dom_workbook=svod_dir / "СВОД_поДЕПО_ДОМ.xlsx",
        depo_ia=prev_svod / "СВОД_поДЕПО.xlsx",
        depo_dom=prev_svod / "СВОД_поДЕПО_ДОМ.xlsx",
        gpb_r_src=period_dir / "GPB" / "R",
        rsd_r_src=period_dir / "RSD" / "R",
        rsd_rep_src=period_dir / "RSD" / "REP",
        report_date=report_date_for_period(period_name),
        year=year,
        month=month,
    )
