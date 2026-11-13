"""Entry point for VINW CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .server import mcp
from .store.project import Project
from .store.registry import ProjectNotFound, ProjectRegistry
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

    # project (multi-project registry)
    p_proj = sub.add_parser("project", help="Manage registered VINW projects")
    proj_sub = p_proj.add_subparsers(dest="project_command")

    pa = proj_sub.add_parser("add", help="Register a project directory")
    pa.add_argument("path")
    pa.add_argument("--name", default="")

    pl = proj_sub.add_parser("list", help="List registered projects")
    pl.add_argument("--missing", action="store_true", help="Show only stale paths")

    pr = proj_sub.add_parser("remove", help="Remove a registration")
    pr.add_argument("target")

    pp = proj_sub.add_parser("prune", help="Drop registrations whose path is gone")
    pp.add_argument("--force", action="store_true", help="Actually delete (default: dry run)")

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
        run_tui(_resolve_tui_target(args.project))
    elif args.command == "init":
        proj = Project.init(Path(args.path), args.name, args.desc)
        print(f"✅ Project initialized: {proj.root}")
        print(f"   Current layer: {proj.get_current_layer()}")
        from vinw.store.project import LAYERS
        print(f"   Layers: {', '.join(LAYERS)}")
    elif args.command == "project":
        _run_project_command(args)
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


def _run_project_command(args) -> None:
    registry = ProjectRegistry()

    if args.project_command == "add":
        try:
            result = registry.add(args.path, args.name or None)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(f"✅ 已登记 {result['name']} → {result['path']}")
        if result.get("warning"):
            print(f"   ⚠️  {result['warning']}")
        return

    if args.project_command == "list":
        entries = registry.list(status="missing" if args.missing else None)
        if not entries:
            print("（尚无已注册工程）运行: vinw project add <path>")
            return
        width = max(len(e.get("name") or "") for e in entries)
        for e in entries:
            status = e.get("status", "ok")
            icon = "●" if status == "ok" else "○"
            note = "" if status == "ok" else "  [路径失效]"
            print(f"{icon} {e.get('name'):<{width}}  {e['path']}{note}")
        return

    if args.project_command == "remove":
        try:
            result = registry.remove(args.target)
        except ProjectNotFound as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(f"✅ 已移除登记 {result['name']}（磁盘文件未改动）")
        return

    if args.project_command == "prune":
        result = registry.prune(force=args.force)
        if not result["candidates"]:
            print("✅ 没有失效登记")
            return
        if result["dry_run"]:
            print(f"将删除 {len(result['candidates'])} 条失效登记（加 --force 执行）:")
            for path, name in result["candidates"].items():
                print(f"  ○ {name}  {path}")
        else:
            print(f"✅ 已删除 {result['pruned']} 条失效登记")
        return

    print("用法: vinw project {add|list|remove|prune}")


def _resolve_tui_target(target: str | None) -> str | None:
    """Let `vinw tui` accept a path or a registered project name."""
    if not target:
        return None
    if Path(target).expanduser().exists():
        return target
    try:
        return str(ProjectRegistry().resolve(target).root)
    except ProjectNotFound as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
