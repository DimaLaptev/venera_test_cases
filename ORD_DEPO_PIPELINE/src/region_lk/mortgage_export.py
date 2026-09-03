"""Экспорт закладных (Mortgages Export) в Excel через CASD API."""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from region_lk.client import CasdAuthError, CasdClient, CasdClientError

# По наблюдениям UI: StatusId=2 и ExecutedDate заполнены → экспорт готов.
DEFAULT_READY_STATUS_IDS = frozenset({2})

DEFAULT_EXPORT_BODY: dict[str, bool] = {
    "addWithoutDrafts": True,
    "addCurrentUserDrafts": True,
    "addOtherUsersDrafts": True,
    "addIncludedInOrders": True,
}


@dataclass(frozen=True)
class ExportStatus:
    account_id: int
    section_id: int
    user_id: int | None
    filter_id: int | None
    status_id: int | None
    data: str | None
    created_date: str | None
    executed_date: str | None
    raw: dict[str, Any]


def export_path(account_id: int, section_id: int) -> str:
    return f"/API/CASD/Export/Mortgages/Accounts/{account_id}/Sections/{section_id}"


def export_data_path(account_id: int, section_id: int) -> str:
    return (
        f"/API/CASD/Export/Mortgages/Data/Accounts/{account_id}/Sections/{section_id}"
    )


def parse_export_status(payload: dict[str, Any]) -> ExportStatus:
    return ExportStatus(
        account_id=int(payload.get("AccountId") or 0),
        section_id=int(payload.get("SectionId") or 0),
        user_id=int(payload["UserId"]) if payload.get("UserId") is not None else None,
        filter_id=int(payload["FilterId"]) if payload.get("FilterId") is not None else None,
        status_id=int(payload["StatusId"]) if payload.get("StatusId") is not None else None,
        data=payload.get("Data"),
        created_date=payload.get("CreatedDate"),
        executed_date=payload.get("ExecutedDate"),
        raw=payload,
    )


def is_export_ready(
    status: ExportStatus,
    *,
    ready_status_ids: frozenset[int] = DEFAULT_READY_STATUS_IDS,
) -> bool:
    if status.data:
        return True
    if status.status_id in ready_status_ids and status.executed_date:
        return True
    if status.status_id in ready_status_ids:
        return True
    return False


class ExportAlreadyExistsError(CasdClientError):
    """POST: на счёте уже есть незакрытый экспорт (часто другой sectionId)."""


def _raise_http(client: CasdClient, response: Any, prefix: str) -> None:
    raise CasdClientError(prefix + "\n" + client.format_error(response))


def response_says_export_exists(text: str) -> bool:
    low = (text or "").lower()
    return "уже существует" in low or "already exists" in low


def _unique_section_ids(*groups: Any) -> list[int]:
    seen: dict[int, None] = {}
    for group in groups:
        if group is None:
            continue
        if isinstance(group, int):
            seen[int(group)] = None
            continue
        for sid in group:
            if sid is None:
                continue
            seen[int(sid)] = None
    return list(seen)


def owner_section_id(status: ExportStatus, fallback: int) -> int:
    """sectionId, на который создали экспорт (для DELETE только он)."""
    if status.section_id:
        return int(status.section_id)
    return int(fallback)


def clear_existing_exports(
    client: CasdClient,
    account_id: int,
    section_ids: list[int],
) -> list[int]:
    """
    Снять живой экспорт счёта: GET по известным разделам, DELETE только
    с тем sectionId, на который экспорт создали.
    """
    deleted: list[int] = []
    for sid in _unique_section_ids(section_ids):
        try:
            status = get_mortgage_export_status(client, account_id, sid)
        except CasdAuthError:
            raise
        except CasdClientError as exc:
            print(
                f"REGION API: не удалось проверить экспорт "
                f"account_id={account_id} section_id={sid}: {exc}",
                flush=True,
            )
            continue
        if status is None:
            continue
        owner = owner_section_id(status, sid)
        print(
            f"REGION API: удаляем существующий экспорт "
            f"account_id={account_id} section_id={owner} "
            f"(найден по GET section_id={sid})",
            flush=True,
        )
        delete_mortgage_export(client, account_id, owner)
        deleted.append(owner)
    return deleted


def start_mortgage_export(
    client: CasdClient,
    account_id: int,
    section_id: int,
    *,
    body: dict[str, Any] | None = None,
) -> ExportStatus | None:
    """POST старт экспорта. Тело — camelCase, как в браузере."""
    payload = dict(body or DEFAULT_EXPORT_BODY)
    response = client.request(
        "POST",
        export_path(account_id, section_id),
        json=payload,
    )
    if response.status_code not in (200, 201, 202, 204):
        if response.status_code == 400 and response_says_export_exists(response.text or ""):
            raise ExportAlreadyExistsError(
                f"Старт экспорта не удался (экспорт уже существует). "
                f"account_id={account_id} section_id={section_id}.\n"
                + client.format_error(response)
            )
        _raise_http(
            client,
            response,
            f"Старт экспорта не удался. account_id={account_id} section_id={section_id}.",
        )
    if response.status_code == 204 or not (response.text or "").strip():
        return None
    try:
        return parse_export_status(response.json())
    except Exception:
        return None


def get_mortgage_export_status(
    client: CasdClient,
    account_id: int,
    section_id: int,
) -> ExportStatus | None:
    """GET статус экспорта. 204 = ещё нет данных."""
    response = client.request("GET", export_path(account_id, section_id))
    if response.status_code == 204:
        return None
    if response.status_code != 200:
        _raise_http(
            client,
            response,
            f"Ошибка статуса экспорта. account_id={account_id} section_id={section_id}.",
        )
    return parse_export_status(response.json())


def wait_mortgage_export_ready(
    client: CasdClient,
    account_id: int,
    section_id: int,
    *,
    poll_interval: float = 2.0,
    timeout: float = 120.0,
    ready_status_ids: frozenset[int] = DEFAULT_READY_STATUS_IDS,
) -> ExportStatus:
    deadline = time.monotonic() + timeout
    last: ExportStatus | None = None
    while time.monotonic() < deadline:
        last = get_mortgage_export_status(client, account_id, section_id)
        if last is not None and is_export_ready(last, ready_status_ids=ready_status_ids):
            return last
        time.sleep(poll_interval)
    raise CasdClientError(
        f"Таймаут ожидания экспорта account={account_id} section={section_id}; "
        f"last={last.raw if last else None}"
    )


def download_mortgage_export_bytes(
    client: CasdClient,
    account_id: int,
    section_id: int,
) -> bytes:
    """GET .../Export/Mortgages/Data/... → JSON Value (Base64) → bytes."""
    response = client.request("GET", export_data_path(account_id, section_id))
    if response.status_code != 200:
        _raise_http(
            client,
            response,
            f"Ошибка скачивания Data экспорта. account_id={account_id} section_id={section_id}.",
        )
    payload = response.json()
    value = payload.get("Value")
    if value is None:
        raise CasdClientError(
            f"В ответе Data нет поля Value: keys={list(payload.keys())}"
        )
    return base64.b64decode(value)


def delete_mortgage_export(
    client: CasdClient,
    account_id: int,
    section_id: int,
) -> None:
    """DELETE статус/файл экспорта (как после клика в UI)."""
    response = client.request("DELETE", export_path(account_id, section_id))
    if response.status_code not in (200, 204):
        _raise_http(
            client,
            response,
            f"Ошибка удаления экспорта. account_id={account_id} section_id={section_id}.",
        )


def save_mortgage_export(
    client: CasdClient,
    account_id: int,
    section_id: int,
    out_dir: Path,
    *,
    start: bool = True,
    cleanup: bool = True,
    poll_interval: float = 2.0,
    wait_timeout: float = 120.0,
    body: dict[str, Any] | None = None,
    filename: str | None = None,
    sibling_section_ids: list[int] | None = None,
) -> Path:
    """
    Полный цикл: очистка слота счёта → POST → poll GET → GET Data → файл → DELETE.
    sibling_section_ids — разделы того же счёта (чтобы найти чужой sectionId для DELETE).
    Имя по умолчанию: export-{sectionId}.xlsx (как в UI).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    probe_ids = _unique_section_ids(sibling_section_ids, section_id)
    posted = False
    try:
        if start:
            clear_existing_exports(client, account_id, probe_ids)
            try:
                start_mortgage_export(client, account_id, section_id, body=body)
            except ExportAlreadyExistsError:
                print(
                    f"REGION API: POST «уже существует», повторная очистка "
                    f"account_id={account_id} section_id={section_id}",
                    flush=True,
                )
                clear_existing_exports(client, account_id, probe_ids)
                start_mortgage_export(client, account_id, section_id, body=body)
            posted = True

        wait_mortgage_export_ready(
            client,
            account_id,
            section_id,
            poll_interval=poll_interval,
            timeout=wait_timeout,
        )
        raw = download_mortgage_export_bytes(client, account_id, section_id)
        name = filename or f"export-{section_id}.xlsx"
        target = out_dir / name
        target.write_bytes(raw)
        return target
    finally:
        if cleanup:
            try:
                if posted:
                    delete_mortgage_export(client, account_id, section_id)
                else:
                    clear_existing_exports(client, account_id, probe_ids)
            except CasdClientError as exc:
                print(
                    f"REGION API: не удалось удалить экспорт после попытки "
                    f"account_id={account_id} section_id={section_id}: {exc}",
                    flush=True,
                )
