from __future__ import annotations

import argparse
import sys

from fromcad2cfd_solidworks import cli as solidworks_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fromcad2cfd",
        description="Agentic automation framework for CAD-to-CFD workflows.",
    )
    parser.add_argument("--version", action="store_true", help="Print package version and exit.")
    sub = parser.add_subparsers(dest="module")
    sub.add_parser("solidworks", help="Run SolidWorks automation commands.")
    sub.add_parser("fluent-meshing", help="Roadmap placeholder.")
    sub.add_parser("fluent-solver", help="Roadmap placeholder.")
    sub.add_parser("post", help="Roadmap placeholder.")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "solidworks":
        return solidworks_cli.main(argv[1:])
    if argv and argv[0] in {"fluent-meshing", "fluent-solver", "post"}:
        print(f"{argv[0]} is a roadmap placeholder in v0.1.0.")
        return 2

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from fromcad2cfd import __version__

        print(__version__)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
