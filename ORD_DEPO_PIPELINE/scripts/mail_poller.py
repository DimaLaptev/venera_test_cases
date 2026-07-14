#!/usr/bin/env python3
"""Слушатель почты: тема Ord <YYYY_MM> → сборка Ord_Quantity."""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))

from config import AppConfig, load_config  # noqa: E402
from mail.imap_client import ImapClient, IncomingMail  # noqa: E402
from mail.smtp_client import SmtpClient  # noqa: E402
from mail.subject import parse_ord_subject  # noqa: E402
from runner import run_ord_period  # noqa: E402


def _smtp_from_config(cfg: AppConfig) -> SmtpClient:
    return SmtpClient(
        host=cfg.mail.server,
        username=cfg.mail.username,
        password=cfg.mail.password,
        from_addr=cfg.mail.address or cfg.mail.recipient,
        port=cfg.mail.smtp_port,
        mock=cfg.mail.mock,
        mock_dir=cfg.pipeline_root / "tmp" / "mail_mock",
    )


def process_once(cfg: AppConfig, seen_periods: set[str]) -> int:
    """Один цикл опроса. Возвращает число запущенных сборок Ord."""
    smtp = _smtp_from_config(cfg)
    processed = 0

    if cfg.mail.mock:
        print("[MAIL_MOCK] опрос IMAP пропущен", flush=True)
        return 0

    missing = [
        name
        for name, val in (
            ("MAIL_SERVER_NAME", cfg.mail.server),
            ("MAIL_1_USERNAME", cfg.mail.username),
            ("MAIL_1_PASSWORD", cfg.mail.password),
        )
        if not val
    ]
    if missing:
        raise RuntimeError(f"Не заданы переменные окружения: {', '.join(missing)}")

    # Сначала fetch + mark_seen, затем долгая сборка — иначе IMAP-сессия
    # обрывается сервером и письмо остаётся UNSEEN (повторный запуск).
    # Повтор по тому же периоду: письмо только помечаем прочитанным, сборку не дублируем.
    jobs: list[tuple[IncomingMail, str]] = []
    with ImapClient(
        host=cfg.mail.server,
        username=cfg.mail.username,
        password=cfg.mail.password,
        port=cfg.mail.imap_port,
    ) as imap:
        unseen = imap.fetch_unseen()
        seen_uids: list[str] = []
        for mail in unseen:
            period = parse_ord_subject(mail.subject)
            if period is None:
                continue
            seen_uids.append(mail.uid)
            if period in seen_periods:
                print(
                    f"Письмо UID={mail.uid} тема={mail.subject!r} → период {period} "
                    f"уже обработан, пропуск сборки",
                    flush=True,
                )
                continue
            print(f"Письмо UID={mail.uid} тема={mail.subject!r} → период {period}", flush=True)
            jobs.append((mail, period))
            seen_periods.add(period)
        if seen_uids:
            imap.mark_seen(seen_uids)

    for mail, period in jobs:
        processed += 1
        try:
            result = run_ord_period(
                cfg.pipeline_root,
                cfg.reports_root,
                period=period,
            )
            if result.ok:
                print(result.message, flush=True)
            else:
                print(result.message, file=sys.stderr, flush=True)
                to_addr = mail.from_addr or cfg.mail.recipient
                if to_addr:
                    smtp.send_error_reply(
                        to_addr=to_addr,
                        period=period,
                        error_text=result.message,
                        original_subject=mail.subject,
                    )
        except Exception:
            err = traceback.format_exc()
            print(err, file=sys.stderr, flush=True)
            to_addr = mail.from_addr or cfg.mail.recipient
            if to_addr:
                smtp.send_error_reply(
                    to_addr=to_addr,
                    period=period,
                    error_text=err,
                    original_subject=mail.subject,
                )
    return processed


def run_loop(cfg: AppConfig, *, once: bool = False) -> int:
    print(
        f"mail poller: interval={cfg.mail.poll_interval_sec}s "
        f"reports_root={cfg.reports_root} mock={cfg.mail.mock}",
        flush=True,
    )
    seen_periods: set[str] = set()
    while True:
        try:
            n = process_once(cfg, seen_periods)
            if n:
                print(f"Запущено сборок Ord: {n}", flush=True)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
        if once:
            return 0
        time.sleep(max(1, cfg.mail.poll_interval_sec))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ORD DEPO mail poller")
    parser.add_argument("--pipeline-root", type=Path, default=PIPELINE_ROOT)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Один цикл опроса и выход",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.pipeline_root)
    return run_loop(cfg, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
