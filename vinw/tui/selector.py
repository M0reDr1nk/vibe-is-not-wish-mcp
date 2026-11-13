"""Project selector modal for the VINW TUI (L3 v0.7)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList, Static
from textual.widgets.option_list import Option


class ProjectSelector(ModalScreen[dict | None]):
    """Let the user pick a registered project or the working-directory project."""

    BINDINGS = [Binding("escape", "cancel", "取消")]

    CSS = """
    ProjectSelector { align: center middle; }
    #selector-box {
        width: 90%;
        max-width: 110;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #selector-title { text-style: bold; margin-bottom: 1; }
    #selector-hint { color: $text-muted; margin-top: 1; }
    """

    def __init__(self, entries: list[dict], cwd_project: dict | None = None):
        super().__init__()
        self.entries = entries
        self.cwd_project = cwd_project

    def compose(self) -> ComposeResult:
        with Vertical(id="selector-box"):
            yield Label("选择要查看的 VINW 工程", id="selector-title")
            yield Static(id="selector-cwd")
            yield OptionList(id="selector-list")
            yield Label(
                "↑↓ 选择 · Enter 确认 · Esc 取消 · 也可以在启动时用 vinw tui <path|name>",
                id="selector-hint",
            )

    def on_mount(self) -> None:
        cwd_line = self.query_one("#selector-cwd", Static)
        if self.cwd_project:
            cwd_line.update(
                f"工作目录工程: {self.cwd_project['name']} @ {self.cwd_project['path']}"
            )
        else:
            cwd_line.update("工作目录不是 VINW 工程")

        options = self.query_one("#selector-list", OptionList)
        if self.cwd_project:
            options.add_option(
                Option(
                    f"▶ 当前工作目录  {self.cwd_project['name']}  ({self.cwd_project['path']})",
                    id=f"cwd::{self.cwd_project['path']}",
                )
            )

        if not self.entries and not self.cwd_project:
            options.add_option(
                Option("（尚无已注册工程）先运行: vinw project add .", id=None, disabled=True)
            )
        for entry in self.entries:
            status = entry.get("status", "ok")
            marker = "●" if status == "ok" else "○"
            label = f"{marker} {entry['name']}  ({entry['path']})"
            if status == "missing":
                label += "  [路径失效]"
            options.add_option(Option(label, id=f"reg::{entry['path']}"))

        if options.option_count:
            options.highlighted = 0
            options.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id or ""
        kind, _, path = option_id.partition("::")
        self.dismiss({"path": path, "kind": kind})

    def action_cancel(self) -> None:
        self.dismiss(None)
