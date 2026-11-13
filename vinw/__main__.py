"""Entry point for VINW CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .server import mcp
from .store.project import Project
from .tui.app import run_tui


def main():
    parser = argparse.ArgumentParser(
        description="VINW: Vibe Is Not Wish — Markdown-first, spiral-ascend workflow engine for strict SE process control"
    )
    sub = parser.add_subparsers(dest="command")

    # server
    p_server = sub.add_parser("server", help="Start MCP Server")
    p_server.add_argument("--http", action="store_true", help="Use Streamable HTTP transport (default: stdio)")
    p_server.add_argument("--host", default="127.0.0.1", help="HTTP host (default: 127.0.0.1)")
    p_server.add_argument("--port", type=int, default=3000, help="HTTP port (default: 3000)")

    # tui
    p_tui = sub.add_parser("tui", help="Start TUI visualization")
    p_tui.add_argument("project", nargs="?", help="Project path to open")

    # init
    p_init = sub.add_parser("init", help="Initialize a new project")
    p_init.add_argument("path", help="Project root directory")
    p_init.add_argument("--name", required=True, help="Project name")
    p_init.add_argument("--desc", default="", help="Project description")

    # status (quick CLI view)
    p_status = sub.add_parser("status", help="Show project status")
    p_status.add_argument("project", help="Project path")

    args = parser.parse_args()

    if args.command == "server":
        if args.http:
            print(f"🌐 VINW HTTP server starting at http://{args.host}:{args.port}/mcp")
            print(f"   Transport: streamable-http")
            print(f"   Ctrl+C to stop")
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
        else:
            mcp.run(transport="stdio")
    elif args.command == "tui":
        run_tui(args.project)
    elif args.command == "init":
        proj = Project.init(Path(args.path), args.name, args.desc)
        print(f"✅ Project initialized: {proj.root}")
        print(f"   Current layer: {proj.get_current_layer()}")
        from vinw.store.project import LAYERS
        print(f"   Layers: {', '.join(LAYERS)}")
    elif args.command == "status":
        proj = Project(Path(args.project))
        manifest = proj.read_manifest()
        print(f"Project: {manifest.get('name')}")
        print(f"Current: descent-{manifest.get('current_descent')} @ {manifest.get('current_layer')}")
        print(f"Pending confirmations: {len([p for p in manifest.get('pending_confirmations', []) if not p.get('resolved_at')])}")
        print(f"Ascents: {len(manifest.get('ascent_history', []))}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
