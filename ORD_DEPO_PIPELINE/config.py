"""Конфигурация ORD_DEPO_PIPELINE из .env (python-dotenv) + настройки SVOD."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PIPELINE_ROOT = Path(__file__).resolve().parent

# --- SVOD: константы (раньше svod/config/paths.yaml) ---
SVOD_DEFAULT_REPORT_DATE = "31.03.2026"
SVOD_REGION_EXCLUDE_ACCOUNTS: list[str] = []
SVOD_DEPOSITORY_ALIASES: dict[str, str] = {
    "банк гпб": "Банк ГПБ АО",
    "банк гпб ао": "Банк ГПБ АО",
}
# Относительные пути legacy-режима (тесты / локальный source под svod/)
SVOD_LEGACY_PATHS: dict[str, str] = {
    "source_root": "source",
    "output_dir": "output",
    "depo_dom": "source/DEPO_DOM.xlsx",
    "depo_ia": "source/DEPO_IA.xlsx",
    "sprav_workbook": "source/SPRAV/Справочник.xlsx",
    "svod_workbook": "output/СВОД_поДЕПО.xlsx",
    "svod_dom_workbook": "output/СВОД_поДЕПО_ДОМ.xlsx",
    "gpb": "source/GPB",
    "rsd_msg": "source/RSD_MSG",
    "rsd_exl": "source/RSD_EXL",
    "region": "source/REGION",
    "vtbsd": "source/VTBSD",
    "staging": "source/_staging",
}


def _ensure_dotenv(pipeline_root: Path | None = None) -> None:
    root = (pipeline_root or PIPELINE_ROOT).resolve()
    load_dotenv(root / ".env", override=False)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return int(raw.strip())


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return float(raw.strip())


def _proxies_from_env() -> Optional[dict[str, str]]:
    """Словарь proxies для requests.Session из REGION_PROXY_URL (http/https)."""
    url = (os.getenv("REGION_PROXY_URL") or "").strip()
    if not url:
        return None
    return {"http": url, "https": url}


@dataclass(frozen=True)
class MailConfig:
    server: str
    username: str
    password: str
    address: str
    recipient: str
    poll_interval_sec: int
    mock: bool
    imap_port: int = 993
    smtp_port: int = 587


@dataclass(frozen=True)
class RegionLkSettings:
    """Учётные данные ЛК Region (CASD) из .env. Не импортирует src/region_lk."""

    base_url: str
    email: str
    password: str
    timeout: float = 30.0
    ssl_verify: bool = True
    proxies: Optional[dict[str, str]] = None
    poll_interval: float = 2.0
    wait_timeout: float = 120.0


@dataclass(frozen=True)
class AppConfig:
    pipeline_root: Path
    reports_root: Path
    mail: MailConfig
    region_lk: RegionLkSettings

    @property
    def sprav_workbook(self) -> Path:
        return self.reports_root / "depo_validation" / "Справочник.xlsx"


@dataclass
class SvodPipelinePaths:
    """Пути сборки СВОД_поДЕПО (period или legacy source/)."""

    pipeline_root: Path
    source_root: Path
    output_dir: Path
    depo_dom: Path
    depo_ia: Path
    sprav_workbook: Path
    svod_workbook: Path
    svod_dom_workbook: Path
    gpb: Path
    rsd_msg: Path
    rsd_exl: Path
    region: Path
    vtbsd: Path
    staging: Path
    report_date: str = SVOD_DEFAULT_REPORT_DATE
    region_exclude_accounts: list[str] = field(default_factory=list)
    depository_aliases: dict[str, str] = field(default_factory=dict)


def get_reports_root(pipeline_root: Path | None = None) -> Path:
    """Корень данных из REPORTS_DEPO_DIRECTORY (.env)."""
    _ensure_dotenv(pipeline_root)
    root = (pipeline_root or PIPELINE_ROOT).resolve()
    reports_raw = os.environ.get("REPORTS_DEPO_DIRECTORY", "").strip().strip("'\"")
    if reports_raw:
        reports_root = Path(reports_raw)
    else:
        reports_root = root.parent
    if not reports_root.is_absolute():
        return (root / reports_root).resolve()
    return reports_root.resolve()


def default_sprav_workbook_path(pipeline_root: Path | None = None) -> Path:
    """Справочник ENC: REPORTS_DEPO_DIRECTORY/depo_validation/Справочник.xlsx."""
    return get_reports_root(pipeline_root) / "depo_validation" / "Справочник.xlsx"


def load_config(pipeline_root: Path | None = None) -> AppConfig:
    root = (pipeline_root or PIPELINE_ROOT).resolve()
    _ensure_dotenv(root)
    reports_root = get_reports_root(root)

    mail = MailConfig(
        server=os.environ.get("MAIL_SERVER_NAME", "").strip(),
        username=os.environ.get("MAIL_1_USERNAME", "").strip(),
        password=os.environ.get("MAIL_1_PASSWORD", "").strip(),
        address=os.environ.get("MAIL_1_ADDRESS", "").strip(),
        recipient=os.environ.get("GPB_VALIDATION_RECIPIENT", "").strip(),
        poll_interval_sec=_env_int("MAIL_POLL_INTERVAL_SEC", 60),
        mock=_env_bool("MAIL_MOCK", False),
        imap_port=_env_int("MAIL_IMAP_PORT", 993),
        smtp_port=_env_int("MAIL_SMTP_PORT", 587),
    )
    region_lk = RegionLkSettings(
        base_url=(os.environ.get("REGION_LK_BASE_URL", "").strip() or "https://lk-test.region-dk.ru").rstrip("/"),
        email=os.environ.get("REGION_LK_EMAIL", "").strip(),
        password=os.environ.get("REGION_LK_PASSWORD", ""),
        timeout=_env_float("REGION_LK_TIMEOUT", 30.0),
        ssl_verify=_env_bool("REGION_LK_SSL_VERIFY", True),
        proxies=_proxies_from_env(),
        poll_interval=_env_float("REGION_LK_POLL_INTERVAL", 2.0),
        wait_timeout=_env_float("REGION_LK_WAIT_TIMEOUT", 120.0),
    )
    return AppConfig(
        pipeline_root=root,
        reports_root=reports_root,
        mail=mail,
        region_lk=region_lk,
    )


def load_svod_config(pipeline_root: Path) -> SvodPipelinePaths:
    """Legacy: пути относительно корня SVOD (для unit-тестов со своим source/)."""
    root = Path(pipeline_root).resolve()

    def resolve(key: str) -> Path:
        raw = SVOD_LEGACY_PATHS[key]
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        return p

    return SvodPipelinePaths(
        pipeline_root=root,
        source_root=resolve("source_root"),
        output_dir=resolve("output_dir"),
        depo_dom=resolve("depo_dom"),
        depo_ia=resolve("depo_ia"),
        sprav_workbook=resolve("sprav_workbook"),
        svod_workbook=resolve("svod_workbook"),
        svod_dom_workbook=resolve("svod_dom_workbook"),
        gpb=resolve("gpb"),
        rsd_msg=resolve("rsd_msg"),
        rsd_exl=resolve("rsd_exl"),
        region=resolve("region"),
        vtbsd=resolve("vtbsd"),
        staging=resolve("staging"),
        report_date=SVOD_DEFAULT_REPORT_DATE,
        region_exclude_accounts=list(SVOD_REGION_EXCLUDE_ACCOUNTS),
        depository_aliases=dict(SVOD_DEPOSITORY_ALIASES),
    )


def load_svod_period_config(
    pipeline_root: Path,
    reports_root: Path,
    period: str,
    *,
    report_date: str | None = None,
) -> SvodPipelinePaths:
    """Пути для периода: {reports}/{period}/_SVOD/… + depo_validation/Справочник.xlsx."""
    # period_utils лежит в ORD src — вызывающий код должен иметь его в sys.path
    from period_utils import report_date_for_period, resolve_svod_period_paths

    paths = resolve_svod_period_paths(reports_root, period)
    rd = report_date or report_date_for_period(period) or SVOD_DEFAULT_REPORT_DATE
    return SvodPipelinePaths(
        pipeline_root=Path(pipeline_root).resolve(),
        source_root=paths.svod_dir,
        output_dir=paths.svod_dir,
        depo_dom=paths.depo_dom,
        depo_ia=paths.depo_ia,
        sprav_workbook=paths.sprav_workbook,
        svod_workbook=paths.svod_workbook,
        svod_dom_workbook=paths.svod_dom_workbook,
        gpb=paths.gpb,
        rsd_msg=paths.rsd_msg,
        rsd_exl=paths.rsd_exl,
        region=paths.region,
        vtbsd=paths.vtbsd,
        staging=paths.staging,
        report_date=rd,
        region_exclude_accounts=list(SVOD_REGION_EXCLUDE_ACCOUNTS),
        depository_aliases=dict(SVOD_DEPOSITORY_ALIASES),
    )
