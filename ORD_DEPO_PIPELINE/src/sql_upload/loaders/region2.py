"""Минимальный helper заголовков Регион2 (без DB/registry)."""

from __future__ import annotations

REGION2_HEADERS = (
    "/ReportHeader/DepoAccount/DepoAccount",
    "/ReportBody/PositionList/Position/DivisionList/Division/DivisionInfo/DivisionName",
    "/ReportBody/PositionList/Position/DivisionList/Division/Quantity",
    "/ReportBody/PositionList/Position/PositionInfo/Mortgage/AgreementNumber",
    "/ReportBody/PositionList/Position/PositionInfo/Mortgage/RegistrationNumber",
)


def _match_header_columns(header_row: list[str]) -> list[int] | None:
    indices: list[int] = []
    for header in REGION2_HEADERS:
        try:
            idx = header_row.index(header)
        except ValueError:
            return None
        indices.append(idx)
    return indices
