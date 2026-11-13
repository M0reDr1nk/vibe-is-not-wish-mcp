"""Textual TUI for SE-MCP v2 — spiral-ascend workflow visualization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..store.project import Project, LAYERS
from ..workflow.state_machine import WorkflowEngine


class SEApp(App):
    """Main TUI application for SE-MCP."""

    # `scroll` (not `auto`): always show the scrollbar so overflow is
    # discoverable; `auto` hides it and content appears silently cropped.
    CSS = """
    Screen { align: center middle; }
    #top-panel { height: 40%; border: solid green; overflow-y: scroll; }
    #mid-panel { height: 35%; border: solid blue; overflow-y: scroll; }
    #bottom-panel { height: 25%; border: solid yellow; overflow-y: scroll; }
    """

    project_path: reactive[str | None] = reactive(None)

    def __init__(self, project_path: str | None = None):
        super().__init__()
        self.project_path = project_path
        self.project: Project | None = None
        if project_path:
            self.project = Project(Path(project_path))

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="top-panel")
        yield Static(id="mid-panel")
        yield Static(id="bottom-panel")
        yield Footer()

    def on_mount(self):
        self.set_interval(2, self.refresh_ui)
        self.refresh_ui()

    def refresh_ui(self):
        """Timer-driven refresh; never let a transient error kill the TUI.

        Files may be mid-rewrite when the MCP server updates them, so keep
        the last good render and surface the error instead of crashing.
        """
        try:
            self._refresh_ui()
        except Exception as e:
            try:
                self.query_one("#bottom-panel", Static).update(
                    Panel(
                        Text(f"刷新出错（保留上次渲染）: {e}", style="red"),
                        title="📝 状态与最近变更",
                        border_style="red",
                    )
                )
            except Exception:
                pass

    def _refresh_ui(self):
        if not self.project:
            self.query_one("#top-panel", Static).update("⚠️ No active project loaded")
            return

        manifest = self.project.read_manifest()
        current = manifest.get("current_layer")
        descent = manifest.get("current_descent", 1)
        layer_states = manifest.get("layer_states", {})
        ascents = manifest.get("ascent_history", [])

        # ── Top: Layer state graph with ascent arrows ───────────
        layers_render = []
        for layer in LAYERS:
            state = layer_states.get(layer, {})
            status = state.get("status", "pending")
            baseline = state.get("latest_baseline", "")
            superseded_by = state.get("superseded_by", "")
            active_ascent = state.get("active_ascent", "")

            if status == "baselined":
                icon, color = "✅", "green"
                extra = f" [{baseline}]" if baseline else ""
            elif status == "in_progress":
                icon, color = "▶", "yellow"
                extra = f" [{baseline}]" if baseline else ""
                if active_ascent:
                    extra += f" ↑{active_ascent}"
            elif status == "superseded":
                icon, color = "❌", "red"
                extra = f" [{baseline}] ↑{superseded_by}" if superseded_by else ""
            else:
                icon, color = "○", "dim"
                extra = ""

            is_current = " [当前]" if layer == current else ""
            text = Text(f"{icon} {layer}{extra}{is_current}", style=color)
            layers_render.append(Panel(text, border_style=color))

        # Ascent history arrows (full reason text; panel scrolls if long)
        arrow_texts = []
        for asc in ascents:
            arrow_texts.append(
                f"{asc['id']}: {asc['from_layer']} → {asc['to_layer']}({asc['to_baseline']})"
                f" | 原因: {asc['reason']}"
            )
        arrows = (
            Text("\n".join(arrow_texts), style="cyan")
            if arrow_texts
            else Text("无上升记录", style="dim")
        )

        top_content = Panel(
            Group(
                Columns(layers_render, equal=True),
                Text(""),
                Panel(arrows, title="↩️ 上升回溯历史", border_style="cyan"),
            ),
            title=f"🌀 层状态图 | 当前: descent-{descent} @ {current}",
            border_style="green",
        )
        self.query_one("#top-panel", Static).update(top_content)

        # ── Mid: Todo + Pending confirmations ───────────────────
        todos = self.project.get_todos()
        pending = manifest.get("pending_confirmations", [])

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Layer", width=16)
        table.add_column("Descent", width=7)
        table.add_column("Type", width=6)
        table.add_column("Item", style="white", overflow="fold")

        # Pending confirmations on top
        for p in pending:
            if not p.get("resolved_at"):
                table.add_row(
                    p.get("layer", "?"),
                    str(p.get("descent", "?")),
                    "🔒",
                    f"[待确认] {p['description'][:60]} (id: {p['id']})",
                    style="yellow",
                )

        for t in todos:
            status = "✅" if t["done"] else "⏳"
            style = "green" if t["done"] else "white"
            table.add_row(t["layer"], str(t["descent"]), status, t["text"], style=style)

        mid_content = Panel(
            table if (todos or pending) else Text("暂无待办", style="dim"),
            title=f"📋 待办 / 待确认 ({len(todos)} todo, {len([p for p in pending if not p.get('resolved_at')])} pending)",
            border_style="blue",
        )
        self.query_one("#mid-panel", Static).update(mid_content)

        # ── Bottom: Recent changelog + Action hints ─────────────
        changelog_path = self.project.vinw_dir / "changelog.md"
        recent = ""
        if changelog_path.exists():
            content = changelog_path.read_text(encoding="utf-8")
            import re

            entries = re.split(r"\n## (chg-\S+)", content)
            parsed = []
            for i in range(1, len(entries), 2):
                body = entries[i + 1] if i + 1 < len(entries) else ""
                parsed.append(f"## {entries[i]}{body[:300]}")
            recent = "\n---\n".join(parsed[-3:]) if parsed else "无记录"

        engine = WorkflowEngine(self.project)
        can_desc, desc_msg, next_layer = engine.can_descend_to_next()

        hints = [
            Text.assemble(("当前轮次: ", "bold"), f"descent-{descent} @ {current}"),
            Text.assemble(
                ("可下降? ", "bold"),
                ("✅ " if can_desc else "❌ ", "green" if can_desc else "red"),
                desc_msg,
            ),
        ]
        if can_desc and next_layer:
            hints.append(
                Text.assemble(
                    ("建议: ", "bold"),
                    f"完成当前层后调用 se_baseline({current}) → se_descend({next_layer})",
                )
            )
        if current == "L5-测试验证":
            hints.append(
                Text.assemble(
                    ("提示: ", "bold yellow"),
                    "若发现设计缺陷，可 se_ascend(L5, L2/L1, baseline, reason) 上升回溯",
                )
            )
        if current == "L2-参考文献与方案搜证汇总":
            hints.append(
                Text.assemble(
                    ("提示: ", "bold yellow"),
                    "若搜证发现需求偏差，可 se_ascend(L2→L1) 回溯修正需求",
                )
            )

        bottom_content = Panel(
            Text("\n").join(hints) + Text("\n\n") + Text(recent, style="dim"),
            title="📝 状态与最近变更",
            border_style="yellow",
        )
        self.query_one("#bottom-panel", Static).update(bottom_content)

    def action_refresh(self):
        self.refresh_ui()


def run_tui(project_path: str | None = None):
    app = SEApp(project_path)
    app.run()
