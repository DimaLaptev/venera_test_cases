"""Тесты prepare SVOD и фильтра даты в имени файла."""

from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from config import RegionLkSettings, _proxies_from_env
from period_utils import (
    SVOD_DIR_NAME,
    filename_matches_period_end,
    previous_period_name,
    report_date_for_period,
)
from region_lk_export import casd_config_from_settings, download_region_mortgage_exports
from svod_prepare import prepare_svod_inputs


def _dummy_lk() -> RegionLkSettings:
    return RegionLkSettings(
        base_url="http://example.test",
        email="user@example.test",
        password="secret",
    )


def test_filename_matches_period_end() -> None:
    assert filename_matches_period_end("R_102_20260630_00221.MSG", "2026_06")
    assert filename_matches_period_end("R_260630_000300008201.MSG", "2026_06")
    assert not filename_matches_period_end("R_102_20260531_00221.MSG", "2026_06")


def test_previous_period_and_report_date() -> None:
    assert previous_period_name("2026_05") == "2026_04"
    assert previous_period_name("2026_01") == "2025_12"
    assert report_date_for_period("2026_06") == "30.06.2026"
    assert report_date_for_period("2026_02") == "28.02.2026"


def test_download_region_requires_credentials() -> None:
    settings = RegionLkSettings(base_url="http://example.test", email="", password="")
    try:
        download_region_mortgage_exports(Path("."), settings)
    except ValueError as exc:
        assert "REGION_LK_EMAIL" in str(exc)
    else:
        raise AssertionError("ожидали ValueError без учётки")


def test_proxies_from_env(monkeypatch) -> None:
    monkeypatch.delenv("REGION_PROXY_URL", raising=False)
    assert _proxies_from_env() is None
    monkeypatch.setenv("REGION_PROXY_URL", "http://user:pass@127.0.0.1:3128")
    assert _proxies_from_env() == {
        "http": "http://user:pass@127.0.0.1:3128",
        "https": "http://user:pass@127.0.0.1:3128",
    }


def test_casd_config_uses_region_proxy_url() -> None:
    settings = RegionLkSettings(
        base_url="http://lk.example.test",
        email="a@b.c",
        password="x",
        proxies={"http": "http://user:pass@127.0.0.1:3128", "https": "http://user:pass@127.0.0.1:3128"},
    )
    cfg = casd_config_from_settings(settings)
    assert cfg.proxies == {
        "http": "http://user:pass@127.0.0.1:3128",
        "https": "http://user:pass@127.0.0.1:3128",
    }
    assert cfg.trust_env is False
    empty = casd_config_from_settings(_dummy_lk())
    assert empty.proxies == {}
    assert empty.trust_env is False


def test_prepare_svod_inputs(tmp_path: Path, monkeypatch) -> None:
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

    seen: list[Path] = []

    def fake_download(out_dir: Path, settings: RegionLkSettings):
        seen.append(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "export-66.xlsx"
        dest.write_bytes(b"xlsx")
        return 1, [f"  REGION API: {dest.name} → {dest}"]

    monkeypatch.setattr("svod_prepare.download_region_mortgage_exports", fake_download)

    result = prepare_svod_inputs(tmp_path, period, region_lk=_dummy_lk())
    assert result.gpb_copied == 1
    assert result.rsd_msg_copied == 1
    assert result.rsd_exl_copied == 2
    assert result.region_downloaded == 1
    svod = period_dir / SVOD_DIR_NAME
    assert seen == [svod / "REGION"]
    assert (svod / "GPB" / "R_102_20260630_001.MSG").is_file()
    assert not (svod / "GPB" / "R_102_20260531_001.MSG").exists()
    assert (svod / "RSD_MSG" / "R_260630_abc.MSG").is_file()
    assert (svod / "RSD_EXL" / "file.zip").is_file()
    assert (svod / "RSD_EXL" / "nested" / "a.xlsx").is_file()
    assert (svod / "REGION" / "export-66.xlsx").is_file()
    assert any("REGION=1" in msg for msg in result.messages)


def test_prepare_svod_inputs_skip_region_download(tmp_path: Path, monkeypatch) -> None:
    period = "2026_06"
    period_dir = tmp_path / period
    gpb_r = period_dir / "GPB" / "R"
    rsd_r = period_dir / "RSD" / "R"
    rsd_rep = period_dir / "RSD" / "REP"
    region = period_dir / SVOD_DIR_NAME / "REGION"
    for d in (gpb_r, rsd_r, rsd_rep, region):
        d.mkdir(parents=True)
    (gpb_r / "R_102_20260630_001.MSG").write_text("gpb-ok", encoding="utf-8")
    (rsd_r / "R_260630_abc.MSG").write_text("rsd-ok", encoding="utf-8")
    (rsd_rep / "file.zip").write_text("zip", encoding="utf-8")
    existing = region / "export-66.xlsx"
    existing.write_bytes(b"keep")

    def boom(*_args, **_kwargs):
        raise AssertionError("API REGION не должен вызываться")

    monkeypatch.setattr("svod_prepare.download_region_mortgage_exports", boom)

    result = prepare_svod_inputs(
        tmp_path, period, region_lk=_dummy_lk(), skip_region_download=True
    )
    assert result.gpb_copied == 1
    assert result.rsd_msg_copied == 1
    assert result.rsd_exl_copied == 1
    assert result.region_downloaded == 0
    assert existing.read_bytes() == b"keep"
    assert any("пропуск API" in msg for msg in result.messages)
