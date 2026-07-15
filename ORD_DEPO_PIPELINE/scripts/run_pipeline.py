#!/usr/bin/env python3
"""CLI: сборка Ord_Quantity из REPORTS_DEPO_DIRECTORY / периода."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "src"))
sys.path.insert(0, str(PIPELINE_ROOT))

from config import load_config  # noqa: E402
from runner import run_ord_period  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ORD DEPO pipeline — сборка Ord_Quantity",
    )
    parser.add_argument(
        "--period",
        type=str,
        default=None,
        help="Имя периода YYYY_MM (каталог под REPORTS_DEPO_DIRECTORY)",
    )
    parser.add_argument(
        "--period-dir",
        type=Path,
        default=None,
        help="Явный путь к каталогу периода",
    )
    parser.add_argument(
        "--pipeline-root",
        type=Path,
        default=PIPELINE_ROOT,
        help="Корень ORD_DEPO_PIPELINE",
    )
    parser.add_argument("--skip-dks", action="store_true")
    parser.add_argument("--skip-reps", action="store_true")
    parser.add_argument("--skip-svod", action="store_true")
    parser.add_argument("--skip-ord", action="store_true")
    parser.add_argument("--init-workbook", action="store_true")
    parser.add_argument("--ensure-reference-sheets", action="store_true")
    args = parser.parse_args(argv)

    if not args.period and not args.period_dir:
        parser.error("Укажите --period или --period-dir")

    cfg = load_config(args.pipeline_root)
    print(f"REPORTS_DEPO_DIRECTORY={cfg.reports_root}", flush=True)
    result = run_ord_period(
        cfg.pipeline_root,
        cfg.reports_root,
        period=args.period,
        period_dir=args.period_dir,
        skip_dks=args.skip_dks,
        skip_reps=args.skip_reps,
        skip_svod=args.skip_svod,
        skip_ord=args.skip_ord,
        init_workbook=args.init_workbook,
        ensure_reference_sheets=args.ensure_reference_sheets,
    )

    def _safe_print(text: str, *, file=sys.stdout) -> None:
        if not text:
            return
        end = "" if text.endswith("\n") else "\n"
        try:
            print(text, end=end, file=file, flush=True)
        except UnicodeEncodeError:
            enc = getattr(file, "encoding", None) or "utf-8"
            payload = (text + end).encode(enc, errors="replace")
            buf = getattr(file, "buffer", None)
            if buf is not None:
                buf.write(payload)
                file.flush()
            else:
                sys.stderr.buffer.write(payload)

    _safe_print(result.stdout)
    _safe_print(result.stderr, file=sys.stderr)
    if result.ok:
        _safe_print(result.message)
        return 0
    _safe_print(result.message, file=sys.stderr)
    return result.exit_code or 1


if __name__ == "__main__":
    raise SystemExit(main())
