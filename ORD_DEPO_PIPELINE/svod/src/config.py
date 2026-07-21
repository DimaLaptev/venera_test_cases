"""Совместимость: PipelinePaths / load_* реэкспорт из ORD_DEPO_PIPELINE/config.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from path_bootstrap import bootstrap

bootstrap()

_ORD_ROOT = Path(__file__).resolve().parents[2]
_MOD_NAME = "ord_depo_config"
_spec = importlib.util.spec_from_file_location(_MOD_NAME, _ORD_ROOT / "config.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Не удалось загрузить {_ORD_ROOT / 'config.py'}")
_ord = importlib.util.module_from_spec(_spec)
sys.modules[_MOD_NAME] = _ord
_spec.loader.exec_module(_ord)

PipelinePaths = _ord.SvodPipelinePaths
load_config = _ord.load_svod_config
load_period_config = _ord.load_svod_period_config

__all__ = [
    "PipelinePaths",
    "load_config",
    "load_period_config",
]
