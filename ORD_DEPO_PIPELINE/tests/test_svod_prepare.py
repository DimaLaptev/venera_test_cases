"""Тесты prepare SVOD и фильтра даты в имени файла."""

from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))

from period_utils import (
    filename_matches_period_end,
    previous_period_name,
    report_date_for_period,
)
from svod_prepare import prepare_svod_inputs


def test_filename_matches_period_end() -> None:
    assert filename_matches_period_end("R_102_20260630_00221.MSG", "2026_06")
    assert filename_matches_period_end("R_260630_000300008201.MSG", "2026_06")
    assert not filename_matches_period_end("R_102_20260531_00221.MSG", "2026_06")


def test_previous_period_and_report_date() -> None:
    assert previous_period_name("2026_05") == "2026_04"
    assert previous_period_name("2026_01") == "2025_12"
    assert report_date_for_period("2026_06") == "30.06.2026"
    assert report_date_for_period("2026_02") == "28.02.2026"


def test_prepare_svod_inputs(tmp_path: Path) -> None:
    period = "2026_06"
    period_dir = tmp_path / period
    gpb_r = period_dir / "GPB" / "R"
    rsd_r = period_dir / "RSD" / "R"
    rsd_rep = period_dir / "RSD" / "REP"
    for d in (gpb_r, rsd_r, rsd_rep):
        d.mkdir(parents=True)
    (gpb_r / "R_102_20260630_001.MSG").write_text("gpb-ok", encoding="utf-8")
    (gpb_r / "R_102_20260531_001.MSG").write_text("gpb-skip", encoding="utf-8")
    (rsd_r / "R_260630_abc.MSG").write_text("rsd-ok", encoding="utf-8")
    (rsd_r / "R_260531_abc.MSG").write_text("rsd-skip", encoding="utf-8")
    (rsd_rep / "file.zip").write_text("zip", encoding="utf-8")
    (rsd_rep / "nested").mkdir()
    (rsd_rep / "nested" / "a.xlsx").write_text("x", encoding="utf-8")

    result = prepare_svod_inputs(tmp_path, period)
    assert result.gpb_copied == 1
    assert result.rsd_msg_copied == 1
    assert result.rsd_exl_copied == 2
    svod = period_dir / "SVOD"
    assert (svod / "GPB" / "R_102_20260630_001.MSG").is_file()
    assert not (svod / "GPB" / "R_102_20260531_001.MSG").exists()
    assert (svod / "RSD_MSG" / "R_260630_abc.MSG").is_file()
    assert (svod / "RSD_EXL" / "file.zip").is_file()
    assert (svod / "RSD_EXL" / "nested" / "a.xlsx").is_file()
