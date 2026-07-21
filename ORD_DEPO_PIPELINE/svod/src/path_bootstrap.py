"""Добавление ORD_DEPO_PIPELINE/src в sys.path для import sql_upload и др."""

from __future__ import annotations

import sys
from pathlib import Path


def bootstrap(project_root: Path | None = None) -> Path:
    """
    project_root — корень ORD_DEPO_PIPELINE (родитель каталога svod/).
    """
    if project_root is None:
        # …/ORD_DEPO_PIPELINE/svod/src/path_bootstrap.py → ORD_DEPO_PIPELINE
        project_root = Path(__file__).resolve().parents[2]
    root = project_root.resolve()
    ord_src = root / "src"
    if str(ord_src) not in sys.path:
        sys.path.insert(0, str(ord_src))
    svod_src = root / "svod" / "src"
    if svod_src.is_dir() and str(svod_src) not in sys.path:
        sys.path.insert(0, str(svod_src))
    return root
