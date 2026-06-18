"""Runnable MCP server entry point for safe HyperMesh Meshing tools."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .instructions import HYPERMESH_MESHING_MCP_INSTRUCTIONS
from .tools import DISABLED_TOOLS, MCP_TOOL_FUNCTIONS, tool_inventory


SERVER_NAME = "fromcad2cfd-hypermesh-meshing"


def server_descriptor() -> dict[str, Any]:
    inventory = tool_inventory()
    return {
        "name": SERVER_NAME,
        "transport": "stdio",
        "status": "ready",
        "tool_count": len(inventory["allowed_tools"]),
        "allowed_tools": inventory["allowed_tools"],
        "disabled_tools": DISABLED_TOOLS,
        "instructions_summary": "Safe HyperMesh CFD meshing workflow tools; no raw Tcl/Python or uncontrolled launch tools.",
    }


def build_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "The MCP Python SDK is not installed. Install with `python -m pip install -e \".[mcp]\"` "
            "or `python -m pip install \"mcp>=1,<2\"`."
        ) from exc
    server = FastMCP(SERVER_NAME, instructions=HYPERMESH_MESHING_MCP_INSTRUCTIONS)
    for function in MCP_TOOL_FUNCTIONS:
        server.tool()(function)
    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fromcad2cfd-hypermesh-meshing-mcp")
    parser.add_argument("--describe", action="store_true", help="Print a non-blocking server descriptor and exit.")
    parser.add_argument("--list-tools", action="store_true", help="Print the safe tool inventory and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        print(json.dumps(server_descriptor(), ensure_ascii=True, indent=2))
        return 0
    if args.list_tools:
        print(json.dumps(tool_inventory(), ensure_ascii=True, indent=2))
        return 0
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
