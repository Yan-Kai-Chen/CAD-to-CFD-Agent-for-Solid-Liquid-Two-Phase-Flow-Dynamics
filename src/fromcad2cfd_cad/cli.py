"""CLI helpers for the common CAD backend layer."""

from __future__ import annotations

import argparse
import json

from .formats import CFD_PREFERRED_FORMATS, normalize_export_format
from .registry import registry


CONTRACT_METHODS = [
    "preflight",
    "create_test_geometry",
    "inspect_model",
    "copy_model_for_edit",
    "edit_parameter_by_exact_name",
    "rebuild_and_validate",
    "export_geometry",
    "write_report",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd cad")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("contract", help="Print the common CAD backend contract.")
    sub.add_parser("list-registered", help="List CAD backends registered in this process.")
    normalize = sub.add_parser("normalize-format", help="Normalize one CAD export format name.")
    normalize.add_argument("format")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "contract":
        print(
            json.dumps(
                {
                    "schema": "fromcad2cfd_cad_backend_contract_v1",
                    "required_methods": CONTRACT_METHODS,
                    "preferred_cfd_export_formats": list(CFD_PREFERRED_FORMATS),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "list-registered":
        print(json.dumps(registry.describe(), indent=2))
        return 0
    if args.command == "normalize-format":
        print(normalize_export_format(args.format))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")
