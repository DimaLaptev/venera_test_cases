"""Smoke: runner без книги-основы; mock SMTP-отбивка."""

from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))

from mail.smtp_client import SmtpClient
from runner import run_ord_period


def test_runner_missing_period_dir(tmp_path: Path) -> None:
    result = run_ord_period(
        PIPELINE_ROOT,
        tmp_path,
        period="2099_01",
    )
    assert not result.ok
    assert result.exit_code == 2
    assert "не найден" in result.message.lower() or "не найден" in result.message


def test_runner_missing_workbook(tmp_path: Path) -> None:
    period = tmp_path / "2026_01"
    period.mkdir()
    result = run_ord_period(
        PIPELINE_ROOT,
        tmp_path,
        period="2026_01",
    )
    assert not result.ok
    assert "файл-основа" in result.message
    assert result.workbook.name == "2026_01_Ord_Quantity.xlsx"


def test_smtp_mock_writes_file(tmp_path: Path) -> None:
    client = SmtpClient(
        host="localhost",
        username="u",
        password="p",
        from_addr="from@example.com",
        mock=True,
        mock_dir=tmp_path,
    )
    out = client.send_error_reply(
        to_addr="to@example.com",
        period="2026_05",
        error_text="boom",
        original_subject="Ord <2026_05>",
    )
    assert out is not None
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "to@example.com" in text
    assert "boom" in text
