"""Entry point for VINW CLI."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .server import mcp
from .store.project import Project, AdoptError
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
    p_init.add_argument(
        "--no-register",
        dest="register",
        action="store_false",
        help="Do not add the project to the registry (temporary projects)",
    )
    p_init.add_argument(
        "--adopt-existing",
        dest="adopt_existing",
        action="store_true",
        help="Adopt an existing code repository as the project root "
        "(non-empty directory allowed; v0.23)",
    )

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

    for cmd, help_text in (("activate", "Mark a project active"),
                           ("deactivate", "Mark a project dormant (skips probing)")):
        sp = proj_sub.add_parser(cmd, help=help_text)
        sp.add_argument("target")

    ph = proj_sub.add_parser("history", help="Show state-transition log for a project")
    ph.add_argument("target")
    ph.add_argument("--limit", type=int, default=20)

    pe = proj_sub.add_parser("export", help="Export registry snapshot as JSON")
    pe.add_argument("--out", default="", help="Write to file instead of stdout")

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
        if getattr(args, "adopt_existing", False):
            # Idempotent adopt: a repo that is already a VINW project is
            # reported, not tracebacked (design-doc v0.23, R36).
            existing = (
                Path(args.path).expanduser().resolve() / ".vinw" / "manifest.md"
            )
            if existing.exists():
                print(f"✅ Already a VINW project: {existing.parent.parent}")
                print("   (idempotent adopt — nothing to do)")
                sys.exit(0)
            try:
                proj = Project.adopt(Path(args.path), args.name, args.desc)
            except (AdoptError, FileNotFoundError, NotADirectoryError) as e:
                print(f"❌ {e}")
                sys.exit(1)
            except FileExistsError:
                print("✅ Already a VINW project (created concurrently).")
                sys.exit(0)
            print(f"✅ Adopted existing repo: {proj.root}")
            print(f"   work_mode: existing-codebase · code_root: .")
            print(f"   Current layer: {proj.get_current_layer()}")
            print(f"   L1 todo seeded with the survey checklist (摸底清单)")
        else:
            proj = Project.init(Path(args.path), args.name, args.desc)
            print(f"✅ Project initialized: {proj.root}")
            print(f"   Current layer: {proj.get_current_layer()}")
            from vinw.store.project import LAYERS
            print(f"   Layers: {', '.join(LAYERS)}")
        if getattr(args, "register", True):
            try:
                registration = ProjectRegistry().add(proj.root)
                name = (
                    registration.get("name")
                    if isinstance(registration, dict)
                    else args.name
                )
                print(f"   Registered as: {name}")
                print(f"   Watch: vinw tui {name}")
                if isinstance(registration, dict) and registration.get("warning"):
                    print(f"   ⚠ {registration['warning']}")
            except (OSError, sqlite3.Error, ValueError) as e:
                print(f"   ⚠ 登记失败（工程已创建）: {e}")
        else:
            print("   (skipped registration)")
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

    if args.project_command in ("activate", "deactivate"):
        state = "active" if args.project_command == "activate" else "dormant"
        try:
            result = registry.set_state(args.target, state)
        except (ProjectNotFound, ValueError) as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(f"✅ {result['name']} → {state}")
        return

    if args.project_command == "history":
        try:
            events = registry.history(args.target, args.limit)
        except ProjectNotFound as e:
            print(f"❌ {e}")
            sys.exit(1)
        if not events:
            print("（无记录）")
            return
        for event in events:
            detail = f"  {event['detail']}" if event.get("detail") else ""
            print(f"{event['at']}  {event['event']:<10}{detail}")
        return

    if args.project_command == "export":
        payload = json.dumps(registry.export_json(), ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(payload + "\n", encoding="utf-8")
            print(f"✅ 已导出到 {args.out}")
        else:
            print(payload)
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
