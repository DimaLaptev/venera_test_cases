"""Копирование входов в {period}/_SVOD перед сборкой СВОД_поДЕПО."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from period_utils import filename_matches_period_end, resolve_svod_period_paths
from region_lk_export import download_region_mortgage_exports


@dataclass(frozen=True)
class PrepareResult:
    gpb_copied: int
    rsd_msg_copied: int
    rsd_exl_copied: int
    region_downloaded: int
    messages: tuple[str, ...]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _copy_matching_files(
    src_dir: Path,
    dst_dir: Path,
    period_name: str,
    *,
    label: str,
) -> tuple[int, list[str]]:
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Нет каталога-источника {label}: {src_dir}")
    _ensure_dir(dst_dir)
    msgs: list[str] = []
    n = 0
    for path in sorted(src_dir.iterdir()):
        if not path.is_file():
            continue
        if not filename_matches_period_end(path.name, period_name):
            continue
        dest = dst_dir / path.name
        shutil.copy2(path, dest)
        n += 1
        msgs.append(f"  {label}: {path.name} → {dest}")
    return n, msgs


def _copy_tree_contents(src_dir: Path, dst_dir: Path, *, label: str) -> tuple[int, list[str]]:
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Нет каталога-источника {label}: {src_dir}")
    _ensure_dir(dst_dir)
    msgs: list[str] = []
    n = 0
    for path in sorted(src_dir.iterdir()):
        dest = dst_dir / path.name
        if path.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(path, dest)
            n += 1
            msgs.append(f"  {label}: {path.name}/ → {dest}/")
        elif path.is_file():
            shutil.copy2(path, dest)
            n += 1
            msgs.append(f"  {label}: {path.name} → {dest}")
    return n, msgs


def prepare_svod_inputs(
    reports_root: Path,
    period_name: str,
    *,
    region_lk: Any = None,
    skip_region_download: bool = False,
) -> PrepareResult:
    """
    GPB/R → _SVOD/GPB (фильтр даты),
    RSD/R → _SVOD/RSD_MSG (фильтр даты),
    RSD/REP → _SVOD/RSD_EXL (всё содержимое),
    CASD API → _SVOD/REGION (Excel для колонки «Состояние»),
    либо skip_region_download: оставить файлы уже лежащие в _SVOD/REGION.
    """
    paths = resolve_svod_period_paths(reports_root, period_name)
    if not paths.period_dir.is_dir():
        raise FileNotFoundError(
            f"Каталог периода не найден: {paths.period_dir} "
            f"(REPORTS_DEPO_DIRECTORY={reports_root})"
        )
    _ensure_dir(paths.svod_dir)

    all_msgs: list[str] = []
    gpb_n, gpb_msgs = _copy_matching_files(
        paths.gpb_r_src, paths.gpb, period_name, label="GPB/R→_SVOD/GPB"
    )
    all_msgs.extend(gpb_msgs)
    rsd_msg_n, rsd_msg_msgs = _copy_matching_files(
        paths.rsd_r_src, paths.rsd_msg, period_name, label="RSD/R→_SVOD/RSD_MSG"
    )
    all_msgs.extend(rsd_msg_msgs)
    rsd_exl_n, rsd_exl_msgs = _copy_tree_contents(
        paths.rsd_rep_src, paths.rsd_exl, label="RSD/REP→_SVOD/RSD_EXL"
    )
    all_msgs.extend(rsd_exl_msgs)

    if skip_region_download:
        region_n = 0
        all_msgs.append(
            f"  REGION: пропуск API, используем файлы в {paths.region}"
        )
    else:
        if region_lk is None:
            from config import load_config

            region_lk = load_config().region_lk
        _ensure_dir(paths.region)
        region_n, region_msgs = download_region_mortgage_exports(paths.region, region_lk)
        all_msgs.extend(region_msgs)

    all_msgs.insert(
        0,
        f"prepare SVOD {period_name}: GPB={gpb_n}, RSD_MSG={rsd_msg_n}, "
        f"RSD_EXL={rsd_exl_n}, REGION={region_n}",
    )
    return PrepareResult(
        gpb_copied=gpb_n,
        rsd_msg_copied=rsd_msg_n,
        rsd_exl_copied=rsd_exl_n,
        region_downloaded=region_n,
        messages=tuple(all_msgs),
    )
