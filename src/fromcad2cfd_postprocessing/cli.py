"""CLI for Fluent postprocessing planning and monitor summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dewaxing_result_pack import (
    dewaxing_result_pack_validation_markdown,
    validate_dewaxing_result_pack,
)
from .monitor_parser import parse_monitor_file
from .summary import compare_summaries, summarize_run
from .video_plan import write_video_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd post")
    sub = parser.add_subparsers(dest="command")

    parse = sub.add_parser("parse-monitor", help="Parse a Fluent report monitor file.")
    parse.add_argument("--monitor", required=True)
    parse.add_argument("--min-columns", type=int, default=2)
    parse.add_argument("--include-rows", action="store_true")

    summary = sub.add_parser("summarize-run", help="Summarize Fluent global and optional wall monitor files.")
    summary.add_argument("--global-monitor", required=True)
    summary.add_argument("--wall-monitor", default=None)
    summary.add_argument("--output-dir", default=None)
    summary.add_argument("--model-name", default="fluent_post_summary")

    video = sub.add_parser("write-video-plan", help="Write a public-safe autosave video frame plan.")
    video.add_argument("--autosave-dir", required=True)
    video.add_argument("--output", required=True)
    video.add_argument("--field", required=True)
    video.add_argument("--time-step-s", type=float, default=0.001)
    video.add_argument("--interval-s", type=float, default=0.1)

    compare = sub.add_parser("compare-runs", help="Compare two summary JSON files.")
    compare.add_argument("--left-summary", required=True)
    compare.add_argument("--right-summary", required=True)

    dewax = sub.add_parser("validate-dewaxing-pack", help="Validate a dewaxing Agent Result Pack.")
    dewax.add_argument("--pack", required=True)
    dewax.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "parse-monitor":
        result = parse_monitor_file(args.monitor, min_columns=args.min_columns, include_rows=args.include_rows)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "parsed" else 2
    if args.command == "summarize-run":
        result = summarize_run(
            args.global_monitor,
            wall_monitor=args.wall_monitor,
            output_dir=args.output_dir,
            model_name=args.model_name,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    if args.command == "write-video-plan":
        result = write_video_plan(
            args.autosave_dir,
            output_path=args.output,
            field=args.field,
            time_step_s=args.time_step_s,
            interval_s=args.interval_s,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "success" else 2
    if args.command == "compare-runs":
        left = json.loads(Path(args.left_summary).read_text(encoding="utf-8"))
        right = json.loads(Path(args.right_summary).read_text(encoding="utf-8"))
        print(json.dumps(compare_summaries(left, right), ensure_ascii=True, indent=2))
        return 0
    if args.command == "validate-dewaxing-pack":
        result = validate_dewaxing_result_pack(args.pack)
        if args.format == "markdown":
            print(dewaxing_result_pack_validation_markdown(result))
        else:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["status"] == "passed" else 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
