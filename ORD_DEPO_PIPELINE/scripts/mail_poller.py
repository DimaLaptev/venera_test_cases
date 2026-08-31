#!/usr/bin/env python3
"""Слушатель почты: Ord <YYYY_MM> / Svod <YYYY_MM> → сборка отчётов."""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from config import AppConfig, load_config  # noqa: E402
from mail.imap_client import ImapClient, IncomingMail  # noqa: E402
from mail.job_cooldown import remaining_cooldown_sec, record_job_start  # noqa: E402
from mail.smtp_client import SmtpClient  # noqa: E402
from mail.subject import parse_ord_subject, parse_svod_subject  # noqa: E402
from runner import run_ord_period  # noqa: E402
from runner_svod import run_svod_period  # noqa: E402


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


def _send_error(
    smtp: SmtpClient,
    cfg: AppConfig,
    mail: IncomingMail,
    *,
    period: str,
    error_text: str,
    report_label: str,
    subject_prefix: str,
) -> None:
    to_addr = mail.from_addr or cfg.mail.recipient
    if not to_addr:
        return
    smtp.send_error_reply(
        to_addr=to_addr,
        period=period,
        error_text=error_text,
        original_subject=mail.subject,
        report_label=report_label,
        subject_prefix=subject_prefix,
    )


def process_once(cfg: AppConfig, last_started: dict[str, float]) -> int:
    """Один цикл опроса. Возвращает число запущенных сборок."""
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
    jobs: list[tuple[IncomingMail, str, str, bool]] = []  # mail, kind, period, skip_region_dl
    with ImapClient(
        host=cfg.mail.server,
        username=cfg.mail.username,
        password=cfg.mail.password,
        port=cfg.mail.imap_port,
    ) as imap:
        unseen = imap.fetch_unseen()
        seen_uids: list[str] = []
        for mail in unseen:
            svod = parse_svod_subject(mail.subject)
            ord_period = parse_ord_subject(mail.subject) if svod is None else None
            skip_region_dl = False
            if svod is not None:
                kind, period = "svod", svod.period
                skip_region_dl = svod.region_from_dir
            elif ord_period is not None:
                kind, period = "ord", ord_period
            else:
                continue
            seen_uids.append(mail.uid)
            job_key = f"{kind}:{period}"
            if skip_region_dl:
                job_key = f"{job_key}:dir"
            left = remaining_cooldown_sec(last_started, job_key)
            if left is not None:
                left_min = max(1, int((left + 59) // 60))
                print(
                    f"Письмо UID={mail.uid} тема={mail.subject!r} → {job_key} "
                    f"уже обработан (осталось {left_min} мин), пропуск сборки",
                    flush=True,
                )
                continue
            print(
                f"Письмо UID={mail.uid} тема={mail.subject!r} → {job_key}",
                flush=True,
            )
            jobs.append((mail, kind, period, skip_region_dl))
            record_job_start(last_started, job_key)
        if seen_uids:
            imap.mark_seen(seen_uids)

    for mail, kind, period, skip_region_dl in jobs:
        processed += 1
        report_label = "СВОД_поДЕПО" if kind == "svod" else "Ord_Quantity"
        subject_prefix = "Svod" if kind == "svod" else "Ord"
        try:
            if kind == "svod":
                result = run_svod_period(
                    cfg.pipeline_root,
                    cfg.reports_root,
                    period=period,
                    region_lk=cfg.region_lk,
                    skip_region_download=skip_region_dl,
                )
            else:
                result = run_ord_period(
                    cfg.pipeline_root,
                    cfg.reports_root,
                    period=period,
                )
            if result.ok:
                print(result.message, flush=True)
            else:
                print(result.message, file=sys.stderr, flush=True)
                _send_error(
                    smtp,
                    cfg,
                    mail,
                    period=period,
                    error_text=result.message,
                    report_label=report_label,
                    subject_prefix=subject_prefix,
                )
        except Exception:
            err = traceback.format_exc()
            print(err, file=sys.stderr, flush=True)
            _send_error(
                smtp,
                cfg,
                mail,
                period=period,
                error_text=err,
                report_label=report_label,
                subject_prefix=subject_prefix,
            )
    return processed


def run_loop(cfg: AppConfig, *, once: bool = False) -> int:
    print(
        f"mail poller: interval={cfg.mail.poll_interval_sec}s "
        f"reports_root={cfg.reports_root} mock={cfg.mail.mock}",
        flush=True,
    )
    last_started: dict[str, float] = {}
    while True:
        try:
            n = process_once(cfg, last_started)
            if n:
                print(f"Запущено сборок: {n}", flush=True)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
        if once:
            return 0
        time.sleep(max(1, cfg.mail.poll_interval_sec))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ORD/SVOD DEPO mail poller")
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
