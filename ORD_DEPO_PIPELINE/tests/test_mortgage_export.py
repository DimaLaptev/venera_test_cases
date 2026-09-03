"""Очистка слота экспорта: DELETE только с sectionId-владельцем."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from unittest.mock import Mock

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from region_lk.client import CasdClientError
from region_lk.mortgage_export import (
    ExportAlreadyExistsError,
    clear_existing_exports,
    response_says_export_exists,
    save_mortgage_export,
    start_mortgage_export,
)


def _resp(status: int, payload: dict | None = None, text: str = ""):
    response = Mock()
    response.status_code = status
    response.reason = "Bad Request" if status >= 400 else "OK"
    if payload is not None:
        response.json.return_value = payload
        response.text = json.dumps(payload)
    else:
        response.json.return_value = {}
        response.text = text
    return response


def _client(side_effect) -> Mock:
    client = Mock()
    client.request.side_effect = side_effect
    client.format_error.return_value = "http-detail"
    return client


def test_response_says_export_exists() -> None:
    assert response_says_export_exists("Запрос на экспорт уже существует")
    assert not response_says_export_exists("Нет доступа")


def test_clear_existing_exports_deletes_owner_section() -> None:
    client = _client(
        [
            _resp(204),
            _resp(
                200,
                {
                    "AccountId": 28,
                    "SectionId": 85,
                    "StatusId": 2,
                    "ExecutedDate": "2026-09-02",
                },
            ),
            _resp(204),
        ]
    )
    deleted = clear_existing_exports(client, 28, [88, 85])
    assert deleted == [85]
    methods = [c.args[0] for c in client.request.call_args_list]
    paths = [c.args[1] for c in client.request.call_args_list]
    assert methods == ["GET", "GET", "DELETE"]
    assert paths[0].endswith("/Sections/88")
    assert paths[1].endswith("/Sections/85")
    assert paths[2].endswith("/Sections/85")


def test_start_raises_already_exists() -> None:
    client = _client([_resp(400, text="Запрос на экспорт уже существует")])
    try:
        start_mortgage_export(client, 28, 88)
    except ExportAlreadyExistsError as exc:
        assert "уже существует" in str(exc)
    else:
        raise AssertionError("ожидали ExportAlreadyExistsError")


def test_save_clears_other_section_then_exports(tmp_path: Path) -> None:
    xlsx = b"PK\x03\x04fake"
    client = _client(
        [
            _resp(
                200,
                {"AccountId": 28, "SectionId": 85, "StatusId": 2, "ExecutedDate": "x"},
            ),
            _resp(204),
            _resp(204),
            _resp(201),
            _resp(
                200,
                {"AccountId": 28, "SectionId": 88, "StatusId": 2, "ExecutedDate": "x"},
            ),
            _resp(200, {"Value": base64.b64encode(xlsx).decode("ascii")}),
            _resp(204),
        ]
    )
    path = save_mortgage_export(
        client,
        28,
        88,
        tmp_path,
        sibling_section_ids=[85, 88],
        poll_interval=0.0,
        wait_timeout=5.0,
    )
    assert path.read_bytes() == xlsx
    methods = [c.args[0] for c in client.request.call_args_list]
    assert methods[0] == "GET"
    assert methods[1] == "DELETE"
    assert methods[1] and client.request.call_args_list[1].args[1].endswith("/Sections/85")
    assert "POST" in methods
    assert methods[-1] == "DELETE"
    assert client.request.call_args_list[-1].args[1].endswith("/Sections/88")


def test_save_retries_post_after_already_exists(tmp_path: Path) -> None:
    xlsx = b"PK\x03\x04retry"
    client = _client(
        [
            _resp(204),
            _resp(204),
            _resp(400, text="Запрос на экспорт уже существует"),
            _resp(
                200,
                {"AccountId": 28, "SectionId": 85, "StatusId": 2, "ExecutedDate": "x"},
            ),
            _resp(204),
            _resp(204),
            _resp(201),
            _resp(
                200,
                {"AccountId": 28, "SectionId": 88, "StatusId": 2, "ExecutedDate": "x"},
            ),
            _resp(200, {"Value": base64.b64encode(xlsx).decode("ascii")}),
            _resp(204),
        ]
    )
    path = save_mortgage_export(
        client,
        28,
        88,
        tmp_path,
        sibling_section_ids=[85],
        poll_interval=0.0,
        wait_timeout=5.0,
    )
    assert path.read_bytes() == xlsx
    posts = [c for c in client.request.call_args_list if c.args[0] == "POST"]
    assert len(posts) == 2


def test_save_deletes_in_finally_if_wait_fails(tmp_path: Path) -> None:
    client = _client(
        [
            _resp(204),
            _resp(201),
            _resp(204),
        ]
    )
    try:
        save_mortgage_export(
            client,
            28,
            88,
            tmp_path,
            sibling_section_ids=[88],
            poll_interval=0.0,
            wait_timeout=0.0,
        )
    except CasdClientError as exc:
        assert "Таймаут" in str(exc)
    else:
        raise AssertionError("ожидали таймаут")
    methods = [c.args[0] for c in client.request.call_args_list]
    assert methods[0] == "GET"
    assert methods[1] == "POST"
    assert methods[-1] == "DELETE"
    assert client.request.call_args_list[-1].args[1].endswith("/Sections/88")
