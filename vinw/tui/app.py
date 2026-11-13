"""Textual TUI for SE-MCP v2 — spiral-ascend workflow visualization."""

from __future__ import annotations

from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..store.project import Project, LAYERS
from ..store.registry import ProjectNotFound, ProjectRegistry, is_vinw_project
from ..workflow.state_machine import WorkflowEngine
from .selector import ProjectSelector


class SEApp(App):
    """Main TUI application for SE-MCP."""

    # Scroll containers must wrap an auto-height Static: a fixed-height Static
    # turns rich renderables into a Visual cropped to the container, so
    # virtual_size never exceeds the viewport and nothing can scroll.
    TITLE = "VINW — Vibe Is Not Wish"

    BINDINGS = [
        Binding("p", "select_project", "切换工程"),
        Binding("r", "refresh", "刷新"),
        Binding("q", "quit", "退出"),
    ]

    CSS = """
    Screen { align: center middle; }
    #workdir-bar { height: auto; padding: 0 1; background: $panel; color: $text-muted; }
    #top-panel { height: 40%; border: solid green; }
    #mid-panel { height: 35%; border: solid blue; }
    #bottom-panel { height: 25%; border: solid yellow; }
    #top-content, #mid-content, #bottom-content { height: auto; }
    """

    project_path: reactive[str | None] = reactive(None)

    def __init__(self, project_path: str | None = None, registry: ProjectRegistry | None = None):
        super().__init__()
        self.project_path = project_path
        self.registry = registry or ProjectRegistry()
        self.workdir = Path.cwd()
        self.project: Project | None = None
        if project_path:
            self.project = self._load_project(project_path)

    def _load_project(self, target: str) -> Project | None:
        """Accept an absolute/relative path or a registered project name."""
        try:
            return self.registry.resolve(target)
        except ProjectNotFound:
            return None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="workdir-bar")
        with VerticalScroll(id="top-panel"):
            yield Static(id="top-content")
        with VerticalScroll(id="mid-panel"):
            yield Static(id="mid-content")
        with VerticalScroll(id="bottom-panel"):
            yield Static(id="bottom-content")
        yield Footer()

    def on_mount(self):
        self._update_workdir_bar()
        self.set_interval(2, self.refresh_ui)
        self.refresh_ui()
        if self.project is None:
            self.call_after_refresh(self.action_select_project)

    def _cwd_project(self) -> dict | None:
        """The VINW project rooted at the working directory, if any."""
        for candidate in (self.workdir / "vinw-design", self.workdir):
            if is_vinw_project(candidate):
                manifest = Project(candidate).read_manifest()
                return {"name": manifest.get("name") or candidate.name, "path": str(candidate.resolve())}
        return None

    def _update_workdir_bar(self) -> None:
        try:
            bar = self.query_one("#workdir-bar", Static)
        except Exception:
            return
        if self.project is not None:
            name = self.project.read_manifest().get("name") or self.project.root.name
            current = f"当前工程: [b]{name}[/b] @ {self.project.root}"
        else:
            current = "当前工程: [i]未选择[/i]（按 p 选择）"
        bar.update(f"工作目录: {self.workdir}    {current}")

    def action_select_project(self) -> None:
        entries = self.registry.list()
        cwd_entry = self._cwd_project()
        self.push_screen(
            ProjectSelector(entries, cwd_entry), callback=self._on_project_selected
        )

    def _on_project_selected(self, choice: dict | None) -> None:
        if not choice:
            return
        try:
            project = Project(Path(choice["path"]))
        except Exception as e:
            self._flash(f"打开工程失败: {e}")
            return
        self.project = project
        self.registry.touch(str(project.root))
        self._update_workdir_bar()
        self.refresh_ui()

    def _flash(self, message: str) -> None:
        try:
            self.query_one("#bottom-content", Static).update(
                Panel(Text(message, style="red"), title="提示", border_style="red")
            )
        except Exception:
            pass

    def refresh_ui(self):
        """Timer-driven refresh; never let a transient error kill the TUI.

        Files may be mid-rewrite when the MCP server updates them, so keep
        the last good render and surface the error instead of crashing.
        """
        try:
            self._refresh_ui()
        except Exception as e:
            try:
                self.query_one("#bottom-content", Static).update(
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
            self.query_one("#top-content", Static).update(
                Panel(
                    Text(
                        "未选择工程。\n\n按 [b]p[/b] 打开工程选择器，"
                        "或用 [b]vinw tui <path|name>[/b] 指定；\n"
                        "尚未登记任何工程时，先运行 [b]vinw project add .[/b]",
                        style="yellow",
                    ),
                    title="⚠️ 没有活动的 VINW 工程",
                    border_style="yellow",
                )
            )
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

            if status == "completed":
                icon, color = "🏁", "bold green"
                extra = ""
            elif status == "baselined":
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
        self.query_one("#top-content", Static).update(top_content)

        # ── Mid: Todo + Pending confirmations ───────────────────
        todos = self.project.get_todos()
        pending = manifest.get("pending_confirmations", [])

        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Layer", min_width=16, max_width=26, overflow="fold")
        table.add_column("Descent", width=7, justify="center")
        table.add_column("状态", width=6, justify="center")
        table.add_column("内容", overflow="fold", ratio=1)

        # Pending confirmations on top
        for p in pending:
            if not p.get("resolved_at"):
                lock = "🔒" if p.get("blocking", True) else "🔓"
                table.add_row(
                    p.get("layer", "?"),
                    str(p.get("descent", "?")),
                    lock,
                    f"[待确认] {p.get('item_type', '')}: {p['description']} (id: {p['id']})",
                    style="yellow",
                )

        for t in todos:
            status = "✅" if t["done"] else "⏳"
            style = "green" if t["done"] else "white"
            table.add_row(t["layer"], str(t["descent"]), status, t["text"], style=style)

        done_count = sum(1 for t in todos if t["done"])
        unresolved = [p for p in pending if not p.get("resolved_at")]
        mid_content = Panel(
            table if (todos or pending) else Text("暂无待办", style="dim"),
            title=(
                f"📋 待办 / 待确认 "
                f"({done_count}/{len(todos)} 已完成, {len(unresolved)} 待确认)"
            ),
            border_style="blue",
        )
        self.query_one("#mid-content", Static).update(mid_content)

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
        self.query_one("#bottom-content", Static).update(bottom_content)

    def action_refresh(self):
        self.refresh_ui()


def run_tui(project_path: str | None = None):
    app = SEApp(project_path)
    app.run()
