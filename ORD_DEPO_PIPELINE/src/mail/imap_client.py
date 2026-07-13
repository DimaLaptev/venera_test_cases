"""IMAP-клиент для опроса входящих писем."""

from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import Message
from typing import Iterable


@dataclass(frozen=True)
class IncomingMail:
    uid: str
    subject: str
    from_addr: str
    raw_subject: str


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_from(msg: Message) -> str:
    raw = msg.get("From", "")
    parsed = email.utils.parseaddr(raw)
    return parsed[1] or raw


class ImapClient:
    def __init__(
        self,
        *,
        host: str,
        username: str,
        password: str,
        port: int = 993,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        self._conn.login(self.username, self.password)
        self._conn.select("INBOX")

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except Exception:
            pass
        try:
            self._conn.logout()
        except Exception:
            pass
        self._conn = None

    def __enter__(self) -> ImapClient:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_unseen(self) -> list[IncomingMail]:
        if self._conn is None:
            raise RuntimeError("IMAP не подключён")
        typ, data = self._conn.search(None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return []
        result: list[IncomingMail] = []
        for uid in data[0].split():
            typ, msg_data = self._conn.fetch(uid, "(RFC822.HEADER)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw)
            subject = _decode_header_value(msg.get("Subject"))
            result.append(
                IncomingMail(
                    uid=uid.decode() if isinstance(uid, bytes) else str(uid),
                    subject=subject,
                    from_addr=_extract_from(msg),
                    raw_subject=msg.get("Subject") or "",
                )
            )
        return result

    def mark_seen(self, uids: Iterable[str]) -> None:
        if self._conn is None:
            return
        for uid in uids:
            self._conn.store(uid.encode() if isinstance(uid, str) else uid, "+FLAGS", "\\Seen")
