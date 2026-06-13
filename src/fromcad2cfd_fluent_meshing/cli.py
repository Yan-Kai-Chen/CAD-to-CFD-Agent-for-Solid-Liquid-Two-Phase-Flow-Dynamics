"""CLI for Fluent Meshing planning helpers."""

from __future__ import annotations

import argparse
import json

from .gate import evaluate_preflight_gate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd fluent-meshing")
    sub = parser.add_subparsers(dest="command")
    gate = sub.add_parser("preflight-gate", help="Evaluate FastCFD evidence before Fluent Meshing preparation.")
    gate.add_argument("--fastcfd-output-dir", required=True, help="FastCFD output directory containing qoi/pilot/lattice artifacts.")
    gate.add_argument("--output-dir", default=None, help="Directory for gate JSON and Markdown reports. Defaults to sibling reports directory.")
    gate.add_argument("--model-name", default="fluent_meshing_preflight_gate", help="Report filename prefix.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "preflight-gate":
        result = evaluate_preflight_gate(
            args.fastcfd_output_dir,
            output_dir=args.output_dir,
            model_name=args.model_name,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 2 if result["status"] == "blocked" else 0
    parser.print_help()
    return 0
