"""Парсинг AccountsSections и discover без сети."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from region_lk.catalog import (
    discover_account_sections,
    fetch_organization_accounts_sections,
    parse_account_section_row,
)
from region_lk.client import CasdClientError


def test_parse_account_section_row() -> None:
    parsed = parse_account_section_row(
        {
            "Account": {
                "Id": 163,
                "Number": "VL0089",
                "Name": "DOM",
                "Organization": {"Name": "org"},
            },
            "Section": {
                "Id": 66,
                "AccountId": 163,
                "Number": "01",
                "Purpose": {"Description": "dep"},
            },
        }
    )
    assert parsed is not None
    account, section = parsed
    assert account.id == 163
    assert account.number == "VL0089"
    assert account.name == "DOM"
    assert section.id == 66
    assert section.account_id == 163
    assert section.number == "01"
    assert section.purpose == "dep"


def test_parse_account_section_row_skips_incomplete() -> None:
    assert parse_account_section_row({"Account": {"Id": 1}}) is None


def test_fetch_organization_accounts_sections_paginates() -> None:
    page0 = Mock()
    page0.status_code = 200
    page0.json.return_value = {
        "CountElements": 2,
        "List": [
            {
                "Account": {"Id": 1, "Number": "VL1"},
                "Section": {"Id": 10, "Number": "A"},
            }
        ],
    }
    page1 = Mock()
    page1.status_code = 200
    page1.json.return_value = {
        "CountElements": 2,
        "List": [
            {
                "Account": {"Id": 1, "Number": "VL1"},
                "Section": {"Id": 11, "Number": "B"},
            }
        ],
    }
    client = Mock()
    client.request.side_effect = [page0, page1]
    pairs = fetch_organization_accounts_sections(client, 13, page_size=1)
    assert [(a.id, s.id, s.number) for a, s in pairs] == [(1, 10, "A"), (1, 11, "B")]
    assert client.request.call_count == 2
    path = client.request.call_args_list[0].args[1]
    assert path == "/API/CASD/Users/Current/Organizations/13/AccountsSections"
    params0 = client.request.call_args_list[0].kwargs["params"]
    assert params0["page"] == 0
    assert params0["countToPage"] == 1
    assert params0["addEmptySections"] is False
    assert client.request.call_args_list[1].kwargs["params"]["page"] == 1


def test_fetch_organization_accounts_sections_http_error() -> None:
    response = Mock()
    response.status_code = 403
    client = Mock()
    client.request.return_value = response
    client.format_error.return_value = "HTTP 403 detail"
    try:
        fetch_organization_accounts_sections(client, 13)
    except CasdClientError as exc:
        assert "organization_id=13" in str(exc)
        assert "HTTP 403 detail" in str(exc)
    else:
        raise AssertionError("ожидали CasdClientError")


def test_discover_account_sections_filters_account() -> None:
    client = SimpleNamespace()
    row_a = {
        "Account": {"Id": 163, "Number": "VL0089"},
        "Section": {"Id": 66, "Number": "01"},
    }
    row_b = {
        "Account": {"Id": 200, "Number": "VL2"},
        "Section": {"Id": 70, "Number": "02"},
    }
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"CountElements": 2, "List": [row_a, row_b]}
    client.request = Mock(return_value=response)
    accounts, pairs = discover_account_sections(client, 13, account_id=163)
    assert [a.id for a in accounts] == [163]
    assert len(pairs) == 1
    assert pairs[0][1].id == 66
