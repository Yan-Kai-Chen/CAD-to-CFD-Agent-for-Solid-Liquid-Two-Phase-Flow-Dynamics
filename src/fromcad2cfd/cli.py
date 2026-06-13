from __future__ import annotations

import argparse
import sys

from fromcad2cfd_cad import cli as cad_cli
from fromcad2cfd_mesh import cli as mesh_cli
from fromcad2cfd_nx import cli as nx_cli
from fromcad2cfd_solidworks import cli as solidworks_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fromcad2cfd",
        description="Agentic automation framework for CAD-to-CFD workflows.",
    )
    parser.add_argument("--version", action="store_true", help="Print package version and exit.")
    sub = parser.add_subparsers(dest="module")
    sub.add_parser("cad", help="Inspect the common CAD backend contract.")
    sub.add_parser("mesh", help="Run mesh preprocessing and coarse solidification commands.")
    sub.add_parser("nx", help="Run Siemens NX controlled-journal backend commands.")
    sub.add_parser("solidworks", help="Run SolidWorks automation commands.")
    sub.add_parser("fluent-meshing", help="Roadmap placeholder.")
    sub.add_parser("fluent-solver", help="Roadmap placeholder.")
    sub.add_parser("post", help="Roadmap placeholder.")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "cad":
        return cad_cli.main(argv[1:])
    if argv and argv[0] == "mesh":
        return mesh_cli.main(argv[1:])
    if argv and argv[0] == "nx":
        return nx_cli.main(argv[1:])
    if argv and argv[0] == "solidworks":
        return solidworks_cli.main(argv[1:])
    if argv and argv[0] in {"fluent-meshing", "fluent-solver", "post"}:
        from fromcad2cfd import __version__

        print(f"{argv[0]} is a roadmap placeholder in v{__version__}.")
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
