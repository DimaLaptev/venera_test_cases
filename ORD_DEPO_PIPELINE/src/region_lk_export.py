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
    organization_id = getattr(settings, "organization_id", None)
    if organization_id is None:
        raise ValueError(
            "Не задан ID организации ЛК Region: REGION_LK_ORGANIZATION_ID"
        )
    organization_id = int(organization_id)

    config = casd_config_from_settings(settings)
    poll_interval = float(getattr(settings, "poll_interval", 2.0))
    wait_timeout = float(getattr(settings, "wait_timeout", 120.0))
    msgs: list[str] = []

    print(
        f"REGION API: авторизация в {config.base_url} …",
        flush=True,
    )
    with CasdClient(config) as client:
        login(client)
        user_id = client.user_id
        try:
            _accounts, pairs = discover_account_sections(client, organization_id)
        except (CasdAuthError, CasdClientError) as exc:
            raise CasdClientError(
                "REGION API: не удалось получить счета/разделы.\n"
                f"base_url={config.base_url}\n"
                f"login_email={email}\n"
                f"user_id={user_id}\n"
                f"organization_id={organization_id}\n\n"
                f"{exc}"
            ) from exc
        print(
            f"REGION API: userId={user_id}, organizationId={organization_id}, "
            f"пар Account/Section={len(pairs)}",
            flush=True,
        )
        if not pairs:
            raise CasdClientError(
                "Пар Account/Section нет — нечего выгружать в _SVOD/REGION"
            )

        nested = len(pairs) > 1
        saved = 0
        errors: list[str] = []
        skip_accounts: set[int] = set()
        sections_by_account: dict[int, list[int]] = {}
        for acc, sec in pairs:
            sections_by_account.setdefault(acc.id, [])
            if sec.id not in sections_by_account[acc.id]:
                sections_by_account[acc.id].append(sec.id)

        for account, section in pairs:
            if account.id in skip_accounts:
                print(
                    f"REGION API: пропуск section_id={section.id} "
                    f"({section.number!r}) — слот счёта account_id={account.id} "
                    f"({account.number!r}) уже с ошибкой",
                    flush=True,
                )
                continue
            target_dir = out_dir / f"account_{account.id}" if nested else out_dir
            try:
                path = save_mortgage_export(
                    client,
                    account.id,
                    section.id,
                    target_dir,
                    poll_interval=poll_interval,
                    wait_timeout=wait_timeout,
                    sibling_section_ids=sections_by_account.get(account.id, []),
                )
                saved += 1
                line = f"  REGION API: {path.name} → {path}"
                print(line, flush=True)
                msgs.append(line)
            except (CasdClientError, CasdAuthError, OSError, ValueError) as exc:
                skip_accounts.add(account.id)
                err_line = (
                    f"account_id={account.id} account_number={account.number!r} "
                    f"section_id={section.id} section_number={section.number!r}:\n{exc}"
                )
                print(f"REGION API ERROR: {err_line}", flush=True)
                errors.append(err_line)
        if errors:
            detail = "\n\n".join(errors)
            raise CasdClientError(
                f"Ошибка выгрузки REGION (saved={saved}, errors={len(errors)}):\n\n{detail}"
            )
        print(f"REGION API: готово, файлов={saved}", flush=True)
        return saved, msgs
