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
from ..workflow.drift import detect_drift, drift_lines
from ..workflow.state_machine import WorkflowEngine
from .selector import ProjectSelector


def build_mid_panel(project, manifest) -> Panel:
    """Build the todo/confirmation panel (pure, unit-testable).

    Extracted from the Textual render path so tests can assert on the actual
    rendered text without reaching into Textual internals (R33-1).
    """
    todos_all = project.get_todos()
    current_descent = manifest.get("current_descent", 1)
    # v0.19：陈旧待办（旧轮次写、从未更新）单独归类，避免"已完成却仍显示未做"
    todos = [t for t in todos_all if t.get("descent") == current_descent]
    stale = [t for t in todos_all if t.get("descent") != current_descent]
    pending = manifest.get("pending_confirmations", [])

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Layer", min_width=16, max_width=26, overflow="fold")
    table.add_column("Descent", width=7, justify="center")
    table.add_column("状态", width=6, justify="center")
    table.add_column("内容", overflow="fold", ratio=1)

    # Pending gates first, blocking group then review group
    open_gates = [p for p in pending if not p.get("resolved_at")]
    blocking_gates = [p for p in open_gates if p.get("blocking", True)]
    review_gates = [p for p in open_gates if not p.get("blocking", True)]

    for label, group, style in (
        ("🔒 阻塞（会卡流程）", blocking_gates, "bold red"),
        ("🔓 待你审阅（不卡流程）", review_gates, "yellow"),
    ):
        if not group:
            continue
        table.add_row(
            label, "", "—", f"共 {len(group)} 项", style=style
        )
        for p in group:
            table.add_row(
                p.get("layer", "?"),
                str(p.get("descent", "?")),
                "🔒" if p.get("blocking", True) else "🔓",
                f"{p.get('item_type', '')}: {p['description']} (id: {p['id']})",
                style=style if p.get("blocking", True) else "yellow",
            )
            # v0.18：澄清项展开显示假设/偏离/参考选项（R33-1）
            if p.get("item_type") == "clarification":
                table.add_row(
                    "", "", "",
                    Text.assemble(
                        ("   假设: ", "bold yellow"),
                        (str(p.get("assumption") or "—"), "yellow"),
                    ),
                )
                table.add_row(
                    "", "", "",
                    f"   偏离: {p.get('deviation') or '—'}",
                )
                rec = p.get("recommendation") or {}
                rec_id = rec.get("id") if isinstance(rec, dict) else None
                opts = [
                    o for o in (p.get("options") or [])
                    if isinstance(o, dict)
                ]
                for idx, opt in enumerate(opts, 1):
                    mark = " ★推荐" if opt.get("id") == rec_id else ""
                    desc = opt.get("description") or ""
                    impact = opt.get("impact") or ""
                    detail = " — ".join(x for x in (desc, impact) if x)
                    table.add_row(
                        "", "", "",
                        f"   [{idx}] {opt.get('label') or opt.get('id')}{mark}"
                        + (f"  ({detail})" if detail else ""),
                    )

    for t in todos:
        status = "✅" if t["done"] else "⏳"
        style = "green" if t["done"] else "white"
        table.add_row(t["layer"], str(t["descent"]), status, t["text"], style=style)

    if stale:
        table.add_row(
            "历史轮次", "—", "🕘",
            f"共 {len(stale)} 条旧轮次未完成项（可能已完成但未更新，按 r 刷新前请核对）",
            style="dim",
        )

    done_count = sum(1 for t in todos if t["done"])
    mid_content = Panel(
        table if (todos or open_gates) else Text("暂无待办", style="dim"),
        title=(
            f"📋 本轮待办 {done_count}/{len(todos)} · 历史 {len(stale)} · "
            f"🔒 阻塞 {len(blocking_gates)} · 🔓 待审阅 {len(review_gates)}"
        ),
        border_style="red" if blocking_gates else "blue",
    )
    return Panel(
        table if (todos or open_gates) else Text("暂无待办", style="dim"),
        title=(
            f"📋 本轮待办 {done_count}/{len(todos)} · 历史 {len(stale)} · "
            f"🔒 阻塞 {len(blocking_gates)} · 🔓 待审阅 {len(review_gates)}"
        ),
        border_style="red" if blocking_gates else "blue",
    )


_CHANGE_STYLE = {
    "baseline": ("green", "基线"),
    "descend": ("cyan", "下降"),
    "ascend": ("red", "上升"),
    "auto-audit": ("yellow", "自动重审"),
    "alignment": ("magenta", "澄清对齐"),
    "assumption-taken": ("yellow", "按假设推进"),
    "repair": ("magenta", "状态修复"),
    "complete": ("bold green", "完成"),
    "purge-confirmations": ("dim", "门控结转"),
}


def build_recent_changes(project, limit: int = 5) -> list[tuple[str, str, str]]:
    """Parse the changelog into (time, kind_label, summary) rows."""
    import re

    path = project.vinw_dir / "changelog.md"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n## (chg-\S+)", content)
    rows: list[tuple[str, str, str]] = []
    for i in range(1, len(blocks), 2):
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        kind = scope = reason = ""
        for line in body.splitlines():
            if line.startswith("| **变更类型**"):
                kind = line.split("|")[2].strip().strip("` ")
            elif line.startswith("| **范围**"):
                scope = line.split("|")[2].strip().strip("` ")
            elif line.startswith("| **原因**"):
                reason = line.split("|")[2].strip()
        when = ""
        m = re.search(r"\[(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", body)
        if m:
            when = f"{m.group(1)[5:]} {m.group(2)}"
        label = _CHANGE_STYLE.get(kind, ("dim", kind or "变更"))[1]
        rows.append((when, label, (reason or scope)[:90]))
    return rows[-limit:][::-1]


def next_action(manifest, drift) -> tuple[str, str]:
    """One-line 'what should happen next', derived from the real state."""
    layers = manifest.get("layer_states", {})
    current = manifest.get("current_layer", "")
    state = (drift or {}).get("state")
    l7 = layers.get("L7-终验", {}).get("status")
    pending = [
        c for c in manifest.get("pending_confirmations", [])
        if not c.get("resolved_at")
    ]
    blocking = [c for c in pending if c.get("blocking")]

    if l7 == "completed" and state not in (None, "clean"):
        return ("red", "完成态已被改动 → se_ascend 回对应层补齐流程")
    if state == "design_lag":
        return ("red", "实现先于设计 → se_ascend 回 L3 补设计")
    if state in ("drifted", "design_synced"):
        return ("yellow", "工作区已漂移 → 重跑 se_check_consistency 并提交审核")
    if blocking:
        clar = [c for c in blocking if c.get("item_type") == "clarification"]
        gates = [c for c in blocking if c.get("item_type") != "clarification"]
        if clar and not gates:
            return ("red", f"{len(clar)} 条阻塞澄清待裁决（按 1-9 选选项 / y 确认假设）")
        if gates:
            return ("red", f"{len(gates)} 条阻塞门控待裁决 → se_resolve_confirmation")
        return ("red", f"{len(blocking)} 条待裁决项")
    if layers.get(current, {}).get("status") == "in_progress":
        return ("yellow", f"当前层进行中 → 完成后 se_baseline({current})")
    if layers.get(current, {}).get("status") == "baselined":
        return ("green", "当前层已冻结 → se_descend 进入下一层")
    return ("dim", "按 se_get_next_steps 推进")


def build_bottom_panel(project, manifest, drift, descent, current) -> Panel:
    """Bottom panel: structured recent changes + the single next action."""
    recent_rows = build_recent_changes(project, limit=5)
    lines = []
    for when, label, summary in recent_rows:
        style = next((st for st, lb in _CHANGE_STYLE.values() if lb == label), "dim")
        lines.append(
            Text.assemble((f"{when}  ", "dim"), (f"[{label}] ", style), (summary, ""))
        )

    sev, action = next_action(manifest, drift)
    body = Text("\n").join(lines) if lines else Text("无变更记录", style="dim")
    return Panel(
        Text.assemble(("下一步: ", "bold"), (action, sev))
        + Text("\n\n")
        + Text("最近变更:", style="bold dim")
        + Text("\n")
        + body,
        title=f"📝 下一步 · 最近 {len(recent_rows)} 条变更（descent-{descent} @ {current}）",
        border_style="red" if sev == "red" else ("yellow" if sev == "yellow" else "blue"),
    )



def build_issue_panel(manifest, drift, detail: str = "") -> Panel | None:
    """One prioritized issue block instead of three overlapping red panels.

    Previously completed-dirty, design-lag and drift each rendered their own
    red panel, so the top looked uniformly red (user report).
    """
    layers = manifest.get("layer_states", {})
    state = (drift or {}).get("state")
    l7_completed = layers.get("L7-终验", {}).get("status") == "completed"

    if l7_completed and state not in (None, "clean"):
        title, severity = "⚠ 完成态已被改动（需上升）", "red"
        lines = [
            "终验之后工作区指纹发生变化，L5/L6/L7 的通过依据已失效。",
            f"漂移类型：{state}（{drift.get('reason')}）",
            "处置：se_ascend 回对应层补齐设计/实现，再重新下降。",
        ]
    elif state == "design_lag":
        title, severity = "🚫 实现先于设计（需上升）", "red"
        lines = [
            "代码已改动但 L3 设计未同步——不接受只改代码不改设计。",
            "处置：se_ascend 回 L3 补设计并基线，再重新审计。",
        ]
    elif state in ("drifted", "design_synced"):
        title, severity = "⚠ 需重新审计", "yellow"
        lines = [
            f"工作区已偏离审计基线（{drift.get('reason')}）。",
            "处置：重跑 se_check_consistency 并提交审核结论。",
        ]
    elif state == "unknown":
        title, severity = "⚠ 漂移未知", "yellow"
        lines = ["无法判定工作区是否与基线一致，不代表一致。"]
    else:
        return None

    if detail:
        # 只保留指纹等明细行；处置建议与变更文件由本面板统一给出，避免重复
        kept = [
            ln for ln in detail.splitlines()
            if ln.strip()
            and not ln.strip().startswith(("处置", "建议", "变更文件"))
            and "处置：" not in ln
            and "建议：" not in ln
        ]
        lines.extend(kept)
    changed = (drift or {}).get("changed") or []
    if changed:
        lines.append("变更文件：" + ", ".join(changed[:4]) + ("…" if len(changed) > 4 else ""))
    return Panel(
        Text("\n".join(lines), style="bold red" if severity == "red" else "yellow"),
        title=title,
        border_style=severity,
    )


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
        # v0.18 harness：对「第一条待裁决澄清」就地选择参考选项
        *[Binding(str(n), f"resolve_option({n})", show=False) for n in range(1, 10)],
        Binding("y", "resolve_assume_ok", "确认假设"),
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
            try:
                name = (
                    self.project.read_manifest().get("name")
                    or self.project.root.name
                )
            except Exception:
                name = self.project.root.name
            current = f"当前工程: [b]{name}[/b] @ {self.project.root}"
        else:
            current = "当前工程: [i]未选择[/i]（按 p 选择）"
        from .. import __commit__, __dirty__, __source_repo__

        version_note = ""
        if __commit__ == "unknown":
            version_note = " | server 版本未知"
        elif __source_repo__:
            import subprocess

            head = subprocess.run(
                ["git", "-C", __source_repo__, "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()[:12]
            dirty_tree = bool(
                subprocess.run(
                    ["git", "-C", __source_repo__, "status", "--porcelain"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
            )
            if head and head != __commit__:
                version_note = (
                    " | ⚠ server 代码陈旧——请重启 MCP server"
                )
            elif __dirty__ or dirty_tree:
                version_note = " | 工作区有未提交改动"
        bar.update(f"工作目录: {self.workdir}    {current}{version_note}")

    # ── 澄清就地裁决（R33-1）────────────────────────────────

    def _first_open_clarification(self) -> dict | None:
        if self.project is None:
            return None
        pending = self.project.read_manifest().get("pending_confirmations", [])
        items = [
            c for c in pending
            if c.get("item_type") == "clarification" and not c.get("resolved_at")
        ]
        if not items:
            return None
        # 阻塞项优先，其次按提出时间
        items.sort(key=lambda c: (0 if c.get("blocking") else 1, c.get("proposed_at") or ""))
        return items[0]

    def _resolve_with(self, resolution: str, feedback: str = "") -> None:
        from ..workflow.state_machine import WorkflowEngine

        cfm = self._first_open_clarification()
        if cfm is None:
            self.notify("没有待裁决的澄清", timeout=2)
            return
        try:
            WorkflowEngine(self.project).resolve_confirmation(
                cfm["id"], resolution, feedback
            )
        except ValueError as e:
            self.notify(f"裁决失败: {e}", timeout=4, severity="error")
            return
        self.notify(f"已裁决 {cfm['id']} → {resolution}", timeout=3)
        self.action_refresh()

    def action_resolve_option(self, index: int) -> None:
        cfm = self._first_open_clarification()
        if cfm is None:
            return
        opts = [o for o in (cfm.get("options") or []) if isinstance(o, dict)]
        if index < 1 or index > len(opts):
            self.notify(f"无第 {index} 个选项", timeout=2)
            return
        self._resolve_with(str(opts[index - 1].get("id")))

    def action_resolve_assume_ok(self) -> None:
        self._resolve_with("assume-ok")

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
        consistency = manifest.get("layer_states", {}).get("L4-编码实现", {}).get(
            "consistency"
        )
        drift = detect_drift(self.project)
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

            # Base style by status; the current layer overrides it below so
            # only one block is visually dominant (otherwise several layers
            # look identically "green" during a transition).
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
                # 上升后"待重做"是正常流程，不是错误——红色只留给问题
                icon, color = "↻", "yellow"
                extra = " [待重做]"
                if baseline:
                    extra += f" [{baseline}]"
                if superseded_by:
                    extra += f" ↑{superseded_by}"
            else:
                icon, color = "○", "dim"
                extra = ""

            drift_active = drift.get("state") not in (None, "clean")
            if (
                drift_active
                and layer in ("L5-测试验证", "L6-检视清理", "L7-终验")
                and status in ("baselined", "completed")
            ):
                icon, color = "⚠", "yellow"
                extra = " [依据失效：代码已变更]"

            is_current_layer = layer == current
            if is_current_layer:
                # Current layer is always the brightest element
                if status == "in_progress":
                    icon, color = "▶", "bold yellow"
                elif status == "completed":
                    icon, color = "🏁", "bold green"
                elif status == "baselined":
                    icon, color = "◆", "bold cyan"
                else:
                    color = "bold"
            elif status in ("baselined", "completed"):
                # Passed baselines recede so they don't compete with the current
                color = "dim green"

            # Auditor state is only meaningful on the L4 block
            if layer == "L4-编码实现" and consistency:
                extra += self._consistency_suffix(consistency)
            if layer == "L4-编码实现" and drift.get("state") in (
                "drifted",
                "design_lag",
                "design_synced",
            ):
                extra += (
                    " 🚫设计滞后"
                    if drift.get("state") == "design_lag"
                    else " ⚠需重审"
                    if drift.get("state") == "design_synced"
                    else " ⚠漂移"
                )
                color = "bold red"
            elif layer == "L4-编码实现" and drift.get("state") == "unknown":
                extra += " ⚠漂移未知"

            is_current = " [当前]" if is_current_layer else ""
            text = Text(f"{icon} {layer}{extra}{is_current}", style=color)
            layers_render.append(Panel(text, border_style=color))

        # Ascent history arrows (full reason text; panel scrolls if long)
        arrow_texts = []
        for asc in ascents:
            arrow_texts.append(
                f"{asc['id']}: {asc['from_layer']} → {asc['to_layer']}({asc['to_baseline']})"
                f" | 原因: {asc['reason']}"
            )
        if len(arrow_texts) > 3:
            arrow_texts = ["…（更早的 %d 条已折叠）" % (len(arrow_texts) - 3)] + arrow_texts[-3:]
        arrow_texts = [t[:110] + ("…" if len(t) > 110 else "") for t in arrow_texts]
        arrows = (
            Text("\n".join(arrow_texts), style="cyan")
            if arrow_texts
            else Text("无上升记录", style="dim")
        )

        children = [
            Columns(layers_render, equal=True),
            Text(""),
        ]
        issue = build_issue_panel(
            manifest, drift, "\n".join(drift_lines(self.project))
        )
        if issue is not None:
            children.append(issue)
            children.append(Text(""))

        children.append(Panel(arrows, title="↩️ 上升回溯历史", border_style="cyan"))

        top_content = Panel(
            Group(*children),
            title=(
                f"🌀 层状态图 | 当前: descent-{descent} @ {current}"
                f"  (◆=当前层 · ✅已基线 · 暗绿=已过 · ↻=待重做)"
                + ("  ⚠漂移" if drift.get("detected") else "")
            ),
            border_style="red" if drift.get("detected") else "green",
        )
        self.query_one("#top-content", Static).update(top_content)

        # ── Mid: 待办 + 待确认（构造含读取，统一在纯函数里做）──────
        self.query_one("#mid-content", Static).update(
            build_mid_panel(self.project, manifest)
        )

        bottom_content = build_bottom_panel(
            self.project, manifest, drift, descent, current
        )
        self.query_one("#bottom-content", Static).update(bottom_content)

    @staticmethod
    def _consistency_suffix(consistency: dict) -> str:
        """Compact audit state for the L4 block: verdict + staleness + conflict."""
        overall = consistency.get("overall") or "?"
        mark = {"passed": "✓", "warning": "!", "config_error": "⚙"}.get(overall, "?")
        suffix = f" chk{mark}"
        if consistency.get("tooling_discrepancy"):
            suffix += "⚠冲突"
        if consistency.get("needs_llm"):
            suffix += "·待审"
        llm = consistency.get("llm_verdict")
        if llm:
            suffix += f"/llm{'✓' if llm == 'passed' else '!'}"
        return suffix

    def action_refresh(self):
        self.refresh_ui()


def run_tui(project_path: str | None = None):
    app = SEApp(project_path)
    app.run()
