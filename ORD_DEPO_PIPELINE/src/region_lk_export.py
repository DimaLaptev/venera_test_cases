"""Выгрузка закладных CASD в каталог _SVOD/REGION (как CLI --all)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from region_lk.auth import login
from region_lk.catalog import discover_account_sections
from region_lk.client import CasdAuthError, CasdClient, CasdClientError
from region_lk.config import RegionLkConfig
from region_lk.mortgage_export import save_mortgage_export


def casd_config_from_settings(settings: Any) -> RegionLkConfig:
    """Маппинг RegionLkSettings (config.py) → RegionLkConfig клиента."""
    proxies = getattr(settings, "proxies", None)
    # Пустой REGION_PROXY_URL → без прокси; не подхватываем HTTP_PROXY из окружения.
    if not proxies:
        proxies = {}
    base = (getattr(settings, "base_url", "") or "").strip().rstrip("/")
    return RegionLkConfig(
        base_url=base,
        email=(getattr(settings, "email", "") or "").strip(),
        password=getattr(settings, "password", "") or "",
        timeout=float(getattr(settings, "timeout", 30.0)),
        ssl_verify=bool(getattr(settings, "ssl_verify", True)),
        proxies=proxies,
        trust_env=False,
    )


def download_region_mortgage_exports(
    out_dir: Path,
    settings: Any,
) -> tuple[int, list[str]]:
    """
    Login → все Accounts/Sections → Excel в out_dir.
    Имена как у CLI: export-{sectionId}.xlsx; при нескольких парах —
    account_{id}/export-{sectionId}.xlsx.
    """
    email = (getattr(settings, "email", "") or "").strip()
    password = getattr(settings, "password", "") or ""
    if not email or not password:
        raise ValueError(
            "Не заданы учётные данные ЛК Region: REGION_LK_EMAIL / REGION_LK_PASSWORD"
        )

    config = casd_config_from_settings(settings)
    poll_interval = float(getattr(settings, "poll_interval", 2.0))
    wait_timeout = float(getattr(settings, "wait_timeout", 120.0))
    msgs: list[str] = []

    with CasdClient(config) as client:
        login(client)
        user_id = client.user_id
        if user_id is None:
            raise CasdClientError(
                "Не удалось взять userId из логина ЛК Region."
            )
        _accounts, pairs = discover_account_sections(client, user_id)
        if not pairs:
            raise CasdClientError(
                "Пар Account/Section нет — нечего выгружать в _SVOD/REGION"
            )

        nested = len(pairs) > 1
        saved = 0
        errors: list[str] = []
        for account, section in pairs:
            target_dir = out_dir / f"account_{account.id}" if nested else out_dir
            try:
                path = save_mortgage_export(
                    client,
                    account.id,
                    section.id,
                    target_dir,
                    poll_interval=poll_interval,
                    wait_timeout=wait_timeout,
                )
                saved += 1
                msgs.append(f"  REGION API: {path.name} → {path}")
            except (CasdClientError, CasdAuthError, OSError, ValueError) as exc:
                errors.append(f"account={account.id} section={section.id}: {exc}")
        if errors:
            detail = "; ".join(errors)
            raise CasdClientError(
                f"Ошибка выгрузки REGION (saved={saved}): {detail}"
            )
        return saved, msgs
