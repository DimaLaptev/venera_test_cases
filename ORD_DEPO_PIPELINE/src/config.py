"""Конфигурация ORD_DEPO_PIPELINE из env и config/paths.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]


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
class AppConfig:
    pipeline_root: Path
    reports_root: Path
    mail: MailConfig

    @property
    def sprav_workbook(self) -> Path:
        return self.reports_root / "depo_validation" / "Справочник.xlsx"


def get_reports_root(pipeline_root: Path | None = None) -> Path:
    """Корень данных из REPORTS_DEPO_DIRECTORY (fallback — родитель пайплайна)."""
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
    return AppConfig(pipeline_root=root, reports_root=reports_root, mail=mail)
