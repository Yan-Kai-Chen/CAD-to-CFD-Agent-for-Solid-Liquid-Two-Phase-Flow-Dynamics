from __future__ import annotations

import argparse
import sys

from fromcad2cfd_cad import cli as cad_cli
from fromcad2cfd_fastcfd import cli as fastcfd_cli
from fromcad2cfd_fluent_meshing import cli as fluent_meshing_cli
from fromcad2cfd_fluent_solver import cli as fluent_solver_cli
from fromcad2cfd_hypermesh_meshing import cli as hypermesh_meshing_cli
from fromcad2cfd_mesh import cli as mesh_cli
from fromcad2cfd_nx import cli as nx_cli
from fromcad2cfd_postprocessing import cli as post_cli
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
    sub.add_parser("fastcfd", help="Run agent-safe FastCFD pilot simulation workflows.")
    sub.add_parser("fluent-meshing", help="Run Fluent Meshing planning gate commands.")
    sub.add_parser("fluent-solver", help="Validate Fluent Solver plans and write public-safe templates.")
    sub.add_parser("hypermesh-meshing", help="Validate HyperMesh CFD meshing plans and write adapter templates.")
    sub.add_parser("post", help="Parse Fluent report monitors and write postprocessing summaries.")
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
    if argv and argv[0] == "fastcfd":
        return fastcfd_cli.main(argv[1:])
    if argv and argv[0] == "fluent-meshing":
        return fluent_meshing_cli.main(argv[1:])
    if argv and argv[0] == "fluent-solver":
        return fluent_solver_cli.main(argv[1:])
    if argv and argv[0] == "hypermesh-meshing":
        return hypermesh_meshing_cli.main(argv[1:])
    if argv and argv[0] == "post":
        return post_cli.main(argv[1:])

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
