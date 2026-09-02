"""HTTP-клиент (HTTP client) CASD на requests.Session."""

from __future__ import annotations

import re
from typing import Any

import requests
import urllib3

from region_lk.config import RegionLkConfig

_MAX_ERROR_BODY = 8000
_RE_ORG_ACCOUNTS = re.compile(r"/Organizations/(\d+)/AccountsSections", re.I)
_RE_USER_ACCOUNTS = re.compile(r"/Users/(\d+)/Accounts", re.I)
_RE_ACCOUNT_ID = re.compile(r"/Accounts?/(\d+)", re.I)
_RE_SECTION_ID = re.compile(r"/Sections/(\d+)", re.I)


class CasdClientError(RuntimeError):
    """Ошибка клиента CASD."""


class CasdAuthError(CasdClientError):
    """Ошибка авторизации (authentication)."""


def format_casd_http_error(
    response: requests.Response,
    *,
    base_url: str,
    email: str,
    user_id: int | None,
    token_len: int,
) -> str:
    """Полное описание ответа API для логов и SMTP (без значения токена)."""
    body = response.text or ""
    body_len = len(body)
    if body_len > _MAX_ERROR_BODY:
        body = body[:_MAX_ERROR_BODY] + f"\n… (обрезано, всего {body_len} символов)"

    path = ""
    try:
        path = response.request.path_url or ""
    except Exception:
        path = ""
    url = getattr(response, "url", "") or ""
    method = ""
    try:
        method = response.request.method or ""
    except Exception:
        method = ""

    note_parts: list[str] = []
    low = f"{path} {url}".lower()
    combined = f"{path} {url}"
    if "accountssections" in low:
        note_parts.append(
            "Шаг: список счетов и разделов организации "
            "(Users/Current/Organizations/{id}/AccountsSections). "
            "Это ещё не экспорт конкретного счёта ДЕПО (VL…)."
        )
    elif "/users/" in low and "/accounts" in low:
        note_parts.append(
            "Шаг: список счетов CASD пользователя ЛК. "
            "Это ещё не экспорт конкретного счёта ДЕПО (VL…) — "
            "номер счёта/раздела на этом запросе неизвестен."
        )
    elif "/export/mortgages" in low:
        note_parts.append("Шаг: экспорт закладных раздела (Excel).")
    elif "/sections" in low:
        note_parts.append("Шаг: список разделов счёта CASD.")
    org_m = _RE_ORG_ACCOUNTS.search(combined)
    if org_m:
        note_parts.append(f"CASD organization_id из URL: {org_m.group(1)}")
    user_m = _RE_USER_ACCOUNTS.search(combined)
    if user_m:
        note_parts.append(f"CASD user_id из URL: {user_m.group(1)}")
    acc_m = _RE_ACCOUNT_ID.search(combined)
    if acc_m and "/users/" not in low and "accountssections" not in low:
        note_parts.append(f"CASD account_id из URL: {acc_m.group(1)}")
    sec_m = _RE_SECTION_ID.search(combined)
    if sec_m:
        note_parts.append(f"CASD section_id из URL: {sec_m.group(1)}")
    note = ("\n".join(note_parts) + "\n") if note_parts else ""

    hdr_lines: list[str] = []
    for key, value in response.headers.items():
        lk = key.lower()
        if "token" in lk or lk in ("authorization", "cookie", "set-cookie"):
            hdr_lines.append(f"  {key}: <скрыто, len={len(value)}>")
        else:
            hdr_lines.append(f"  {key}: {value}")
    headers_block = "\n".join(hdr_lines) if hdr_lines else "  (нет)"

    return (
        f"{note}"
        f"HTTP {response.status_code} {response.reason or ''}\n"
        f"method: {method}\n"
        f"url: {url}\n"
        f"base_url: {base_url}\n"
        f"login_email: {email}\n"
        f"user_id: {user_id}\n"
        f"token_len: {token_len} (значение токена не передаём)\n"
        f"response_headers:\n{headers_block}\n"
        f"response_body:\n{body}"
    )


class CasdClient:
    def __init__(self, config: RegionLkConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.trust_env = config.trust_env
        if config.proxies is not None:
            self.session.proxies.update(config.proxies)
        self.session.headers.update({"Accept": "application/json"})
        self.session.verify = config.ssl_verify
        if not config.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._token: str | None = None
        self.user_id: int | None = None

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> CasdClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.config.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        require_auth: bool = True,
    ) -> requests.Response:
        headers: dict[str, str] = {}
        if require_auth:
            if not self._token:
                raise CasdAuthError("AuthenticateToken не установлен: сначала вызовите login()")
            headers["AuthenticateToken"] = self._token

        response = self.session.request(
            method,
            self._url(path),
            params=params,
            json=json,
            headers=headers,
            timeout=self.config.timeout,
        )
        if require_auth and response.status_code in (401, 403):
            raise CasdAuthError(self.format_error(response))
        return response

    def format_error(self, response: requests.Response) -> str:
        """Полное описание HTTP-ошибки без значения токена."""
        return format_casd_http_error(
            response,
            base_url=self.config.base_url,
            email=self.config.email,
            user_id=self.user_id,
            token_len=len(self._token or ""),
        )

    def set_token(self, token: str) -> None:
        self._token = token
        self.session.headers["AuthenticateToken"] = token
