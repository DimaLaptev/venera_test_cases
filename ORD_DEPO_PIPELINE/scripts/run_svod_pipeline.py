#!/usr/bin/env python3
"""CLI: сборка СВОД_поДЕПО для периода (prepare + pipeline)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from config import load_config
from runner_svod import run_svod_period


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SVOD DEPO for period")
    parser.add_argument("--pipeline-root", type=Path, default=PIPELINE_ROOT)
    parser.add_argument("--period", type=str, required=True, help="YYYY_MM")
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="Не копировать GPB/R, RSD/R, RSD/REP и не выгружать REGION по API",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.pipeline_root)
    result = run_svod_period(
        args.pipeline_root,
        cfg.reports_root,
        period=args.period,
        skip_prepare=args.skip_prepare,
        region_lk=cfg.region_lk,
    )
    if result.stdout:
        print(result.stdout, flush=True)
    if result.ok:
        print(result.message, flush=True)
        return 0
    print(result.message, file=sys.stderr, flush=True)
    return result.exit_code or 1


if __name__ == "__main__":
    raise SystemExit(main())
