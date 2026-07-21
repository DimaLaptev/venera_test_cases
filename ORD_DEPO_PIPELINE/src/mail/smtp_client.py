"""SMTP-отправка отбивок об ошибках."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path


class SmtpClient:
    def __init__(
        self,
        *,
        host: str,
        username: str,
        password: str,
        from_addr: str,
        port: int = 587,
        mock: bool = False,
        mock_dir: Path | None = None,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.port = port
        self.mock = mock
        self.mock_dir = mock_dir

    def send_error_reply(
        self,
        *,
        to_addr: str,
        period: str,
        error_text: str,
        original_subject: str | None = None,
        report_label: str = "Ord_Quantity",
        subject_prefix: str = "Ord",
    ) -> Path | None:
        subject = f"Re: {subject_prefix} <{period}> — ошибка сборки"
        if original_subject:
            subject = f"Re: {original_subject}"
        body = (
            f"Сборка отчёта {report_label} для периода {period} завершилась с ошибкой.\n\n"
            f"{error_text}\n"
        )
        msg = EmailMessage()
        msg["From"] = self.from_addr
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        if self.mock:
            out_dir = self.mock_dir or Path(".")
            out_dir.mkdir(parents=True, exist_ok=True)
            kind = "svod" if subject_prefix.lower() == "svod" else "ord"
            out = out_dir / f"mock_reply_{kind}_{period}.txt"
            out.write_text(
                f"To: {to_addr}\nSubject: {subject}\n\n{body}",
                encoding="utf-8",
            )
            print(f"[MAIL_MOCK] отбивка записана: {out}", flush=True)
            return out

        with smtplib.SMTP(self.host, self.port, timeout=60) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.username, self.password)
            smtp.send_message(msg)
        return None
