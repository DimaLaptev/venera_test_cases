"""Полный текст HTTP-ошибок CASD для логов и SMTP (без токена)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from runner import RunResult, format_failure_email_text
from region_lk.client import format_casd_http_error


def _response(
    *,
    status: int = 403,
    reason: str = "Forbidden",
    text: str = "Нет доступа для совершения операции",
    url: str = "https://lk.region-dk.ru/API/CASD/Users/183/Accounts",
    path: str = "/API/CASD/Users/183/Accounts",
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> Mock:
    request = Mock()
    request.path_url = path
    request.method = method
    response = Mock()
    response.status_code = status
    response.reason = reason
    response.text = text
    response.url = url
    response.request = request
    response.headers = headers or {
        "Content-Type": "application/json",
        "AuthenticateToken": "secret-token-value-must-not-leak",
    }
    return response


def test_format_casd_http_error_403_user_accounts() -> None:
    text = format_casd_http_error(
        _response(),
        base_url="https://lk.region-dk.ru",
        email="ops@example.com",
        user_id=183,
        token_len=64,
    )
    assert "HTTP 403" in text
    assert "GET" in text
    assert "/API/CASD/Users/183/Accounts" in text
    assert "base_url: https://lk.region-dk.ru" in text
    assert "login_email: ops@example.com" in text
    assert "user_id: 183" in text
    assert "token_len: 64" in text
    assert "Нет доступа для совершения операции" in text
    assert "список счетов CASD" in text
    assert "CASD user_id из URL: 183" in text
    assert "secret-token-value-must-not-leak" not in text
    assert "скрыто" in text


def test_format_casd_http_error_includes_account_and_section_from_url() -> None:
    text = format_casd_http_error(
        _response(
            url="https://lk.region-dk.ru/API/CASD/Export/Mortgages/Accounts/42/Sections/85",
            path="/API/CASD/Export/Mortgages/Accounts/42/Sections/85",
        ),
        base_url="https://lk.region-dk.ru",
        email="ops@example.com",
        user_id=183,
        token_len=64,
    )
    assert "экспорт закладных" in text
    assert "CASD account_id из URL: 42" in text
    assert "CASD section_id из URL: 85" in text


def test_format_failure_email_text_includes_stdout() -> None:
    result = RunResult(
        ok=False,
        period_name="2026_05",
        period_dir=Path("."),
        workbook=Path("."),
        exit_code=2,
        message="Ошибка сборки СВОД_поДЕПО для 2026_05: код 1",
        stdout="REGION API ERROR: account_id=42 account_number='VL0089'",
        stderr="HTTP 403 Forbidden",
    )
    text = format_failure_email_text(result)
    assert "код 1" in text
    assert "account_number='VL0089'" in text
    assert "HTTP 403 Forbidden" in text
    assert "--- stdout ---" in text
    assert "--- stderr ---" in text
