"""Smoke tests for the TUI (headless via textual run_test)."""

import asyncio
import shutil

import pytest

from textual.widgets import Static

from vinw.store.project import Project
from vinw.tui.app import SEApp
from vinw.tui.selector import ProjectSelector


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "tui-proj"
    p = Project.init(root, "tui-proj", "TUI smoke test")
    yield p
    shutil.rmtree(root, ignore_errors=True)


def _run(app, coro_fn):
    async def runner():
        async with app.run_test(size=(110, 30)) as pilot:
            await coro_fn(pilot)

    asyncio.run(runner())


def test_tui_renders_with_project(proj):
    """Full render path must not raise and must fill all three panels."""
    app = SEApp(str(proj.root))

    async def scenario(pilot):
        await pilot.pause()
        for pid in ("#top-content", "#mid-content", "#bottom-content"):
            widget = app.query_one(pid)
            assert widget.content

    _run(app, scenario)


def test_tui_renders_without_project():
    """No-project path shows guidance and opens the selector instead of crashing."""
    app = SEApp(None)

    async def scenario(pilot):
        await pilot.pause()
        panel = app.query_one("#top-content").content
        assert "没有活动的 VINW 工程" in str(getattr(panel, "title", panel))
        # Selector is pushed automatically when no project was given
        if isinstance(app.screen, ProjectSelector):
            app.pop_screen()

    _run(app, scenario)


def test_tui_refresh_after_workflow_changes(proj):
    """Re-render after manifest mutations (e.g. ascend marks superseded)."""
    app = SEApp(str(proj.root))

    async def scenario(pilot):
        await pilot.pause()
        manifest = proj.read_manifest()
        manifest["layer_states"]["L1-需求拆解"] = {
            "status": "superseded",
            "superseded_by": "asc-999",
            "latest_baseline": "v001",
        }
        proj.write_manifest(manifest)
        app.refresh_ui()
        await pilot.pause()
        assert app.query_one("#top-content").content

    _run(app, scenario)


def test_tui_survives_transient_file_error(proj):
    """A mid-rewrite/corrupt manifest must not kill the refresh loop."""
    app = SEApp(str(proj.root))

    async def scenario(pilot):
        await pilot.pause()
        (proj.root / ".vinw" / "manifest.md").unlink()
        app.refresh_ui()  # must not raise
        await pilot.pause()
        panel = app.query_one("#bottom-content").content
        assert "刷新出错" in str(getattr(panel, "renderable", panel))

    _run(app, scenario)


def test_todo_panel_is_actually_scrollable(proj):
    """Overflowing todo content must produce a real scroll range.

    Regression: a fixed-height Static wrapping a rich renderable is cropped
    to the viewport, so max_scroll_y stays 0 and the scrollbar never appears.
    """
    app = SEApp(str(proj.root))

    async def scenario(pilot):
        await pilot.pause()
        readme = proj.read_layer_readme("L1-需求拆解")
        todos = "\n".join(f"- [ ] 滚动测试待办 {i}" for i in range(40))
        content = readme["content"].split("## 当前待办")[0] + "## 当前待办\n\n" + todos + "\n"
        proj.write_layer_readme("L1-需求拆解", readme, content)
        app.refresh_ui()
        await pilot.pause()
        panel = app.query_one("#mid-panel")
        assert panel.max_scroll_y > 0, "todo panel has no scrollable overflow"
        # And it must really scroll
        panel.scroll_end(animate=False)
        await pilot.pause()
        assert panel.scroll_y > 0

    _run(app, scenario)


# ── Multi-project TUI (L3 v0.7) ─────────────────────────────


@pytest.fixture
def registry_home(tmp_path, monkeypatch):
    monkeypatch.setenv("VINW_HOME", str(tmp_path / "home"))
    from vinw.store.registry import ProjectRegistry

    reg = ProjectRegistry()
    roots = []
    for i in range(2):
        root = tmp_path / f"proj-{i}"
        p = Project.init(root, f"proj-{i}", f"project {i}")
        reg.add(root, name=f"proj-{i}")
        roots.append(p)
    return reg, roots


def test_workdir_bar_shows_cwd_and_project(registry_home, monkeypatch):
    reg, roots = registry_home
    monkeypatch.chdir(roots[0].root)
    app = SEApp(str(roots[0].root), registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        bar = str(app.query_one("#workdir-bar").content)
        assert "工作目录" in bar
        assert "proj-0" in bar

    _run(app, scenario)


def test_selector_lists_registered_projects(registry_home):
    reg, roots = registry_home
    app = SEApp(None, registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        from vinw.tui.selector import ProjectSelector

        assert isinstance(app.screen, ProjectSelector)
        options = app.screen.query_one("#selector-list")
        labels = [str(options.get_option_at_index(i).prompt) for i in range(options.option_count)]
        assert any("proj-0" in label for label in labels)
        assert any("proj-1" in label for label in labels)

    _run(app, scenario)


def test_switching_project_updates_view(registry_home):
    reg, roots = registry_home
    app = SEApp(str(roots[0].root), registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        assert "proj-0" in str(app.query_one("#workdir-bar").content)
        app._on_project_selected({"path": str(roots[1].root), "kind": "reg"})
        await pilot.pause()
        assert app.project.root == roots[1].root.resolve()
        assert "proj-1" in str(app.query_one("#workdir-bar").content)

    _run(app, scenario)


def test_tui_accepts_registered_name(registry_home):
    reg, roots = registry_home
    app = SEApp("proj-1", registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        assert app.project is not None
        assert app.project.root == roots[1].root.resolve()

    _run(app, scenario)


def test_consistency_marker_on_l4_block(registry_home, monkeypatch):
    """GAP-003: the layer graph must surface the audit state."""
    from vinw.store.project import replace_todo_section

    reg, roots = registry_home
    proj = roots[0]
    (proj.root / "main.py").write_text("def main():\n    return 0\n")
    r = proj.read_layer_readme("L4-编码实现")
    proj.write_layer_readme(
        "L4-编码实现",
        {**r, "todo_descent": 1},
        replace_todo_section(r["content"], "## 当前待办\n\n- [x] 实现"),
    )

    from vinw.workflow.consistency_gate import ConsistencyGate

    ConsistencyGate(proj).ensure()

    app = SEApp(str(proj.root), registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        suffix = app._consistency_suffix(
            app.project.read_manifest()["layer_states"]["L4-编码实现"]["consistency"]
        )
        assert "chk" in suffix
        assert "✓" in suffix

    _run(app, scenario)


def test_only_current_layer_is_visually_dominant(registry_home, monkeypatch):
    """Regression: during layer transitions several blocks looked identically green."""
    from rich.console import Console

    reg, roots = registry_home
    proj = roots[0]
    manifest = proj.read_manifest()
    manifest["current_layer"] = "L5-测试验证"
    manifest["layer_states"] = {
        layer: {"status": "baselined", "latest_baseline": "v001"}
        for layer in (
            "L1-需求拆解",
            "L2-参考文献与方案搜证汇总",
            "L3-方案细化",
            "L4-编码实现",
            "L5-测试验证",
        )
    }
    proj.write_manifest(manifest)

    app = SEApp(str(proj.root), registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        console = Console(width=100, record=True)
        console.print(app.query_one("#top-content").content)
        text = console.export_text()

        # exactly one dominant block (the legend also prints the glyph)
        blocks = [line for line in text.splitlines() if "│ │ ◆" in line]
        assert len(blocks) == 1, text
        assert "L5-测试验证" in blocks[0]
        # passed baselines keep the ✅ icon (the legend also shows one)
        body = "\n".join(
            line for line in text.splitlines() if "层状态图" not in line
        )
        assert body.count("✅") == 4
        assert "▶ L5-测试验证" not in text

    _run(app, scenario)


def test_drift_warning_is_visible(registry_home):
    """A completed-looking project must not read as all-green after code drift."""
    from rich.console import Console

    from vinw.workflow.consistency_gate import ConsistencyGate

    reg, roots = registry_home
    proj = roots[0]
    (proj.root / "main.py").write_text("def main():\n    return 0\n")
    ConsistencyGate(proj).ensure()

    # change the code after the audit
    (proj.root / "main.py").write_text("def main():\n    return 99\n")

    app = SEApp(str(proj.root), registry=reg)

    async def scenario(pilot):
        await pilot.pause()
        console = Console(width=110, record=True)
        console.print(app.query_one("#top-content").content)
        text = console.export_text()
        # code-only change => design lag, which is called out explicitly
        assert "实现先于设计" in text
        assert "实现跑在设计前面" in text
        assert "🚫设计滞后" in text

    _run(app, scenario)


class TestClarificationTui:
    """R33-1: clarification details render, and keys resolve in place."""

    def _seed(self, proj):
        from vinw.workflow.state_machine import WorkflowEngine

        engine = WorkflowEngine(proj)
        return engine.require_confirmation(
            item_type="clarification",
            description="分块取哪一种？",
            options=["4x8", "6x16", "assume-ok", "other"],
            blocking=True,
            extra={
                "layer": "L3-方案细化",
                "question": "分块取哪一种？",
                "uncertainty": "两种都合理",
                "assumption": "取 4x8",
                "deviation": "packing 布局不同",
                "topic_normalized": "tile",
                "options": [
                    {"id": "4x8", "label": "4x8"},
                    {"id": "6x16", "label": "6x16", "impact": "+40%"},
                    {"id": "assume-ok", "label": "确认当前假设"},
                    {"id": "other", "label": "其他"},
                ],
                "recommendation": {"id": "4x8", "reason": "省寄存器"},
                "impact": "high",
                "reversibility": "irreversible",
            },
        )

    def test_details_render(self, proj):
        from rich.console import Console

        from vinw.tui.app import build_mid_panel

        self._seed(proj)
        panel = build_mid_panel(proj, proj.read_manifest())
        console = Console(width=160, record=True)
        console.print(panel)
        rendered = console.export_text()

        assert "假设" in rendered
        assert "取 4x8" in rendered
        assert "偏离" in rendered
        assert "★推荐" in rendered
        assert "[2] 6x16" in rendered

    def test_option_key_resolves(self, proj):
        cfm_id = self._seed(proj)

        async def run():
            app = SEApp(str(proj.root))
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.press("2")   # 第 2 个选项 = 6x16
                await pilot.pause()

        import asyncio

        asyncio.run(run())
        manifest = proj.read_manifest()
        cfm = next(c for c in manifest["pending_confirmations"] if c["id"] == cfm_id)
        assert cfm["resolution"] == "6x16"
        assert cfm["corrected"] is True
        changelog = (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        assert "alignment" in changelog

    def test_assume_ok_key_confirms(self, proj):
        cfm_id = self._seed(proj)

        async def run():
            app = SEApp(str(proj.root))
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                await pilot.press("y")
                await pilot.pause()

        import asyncio

        asyncio.run(run())
        cfm = next(
            c for c in proj.read_manifest()["pending_confirmations"]
            if c["id"] == cfm_id
        )
        assert cfm["resolution"] == "assume-ok"
        assert cfm["corrected"] is False


class TestTodoStaleness:
    """User report: completed work still showed as pending because a
    baselined layer's todo list is never revisited."""

    def test_stale_todos_are_separated(self, proj):
        from rich.console import Console

        from vinw.store.project import replace_todo_section
        from vinw.tui.app import build_mid_panel

        manifest = proj.read_manifest()
        manifest["current_descent"] = 5
        proj.write_manifest(manifest)

        # 旧轮次写下的待办（descent 1），其中含未完成项
        readme = proj.read_layer_readme("L1-需求拆解")
        proj.write_layer_readme(
            "L1-需求拆解",
            {**readme, "todo_descent": 1},
            replace_todo_section(
                readme["content"], "## 当前待办\n\n- [ ] 旧轮次遗留项"
            ),
        )
        # 本轮待办
        readme2 = proj.read_layer_readme("L2-参考文献与方案搜证汇总")
        proj.write_layer_readme(
            "L2-参考文献与方案搜证汇总",
            {**readme2, "todo_descent": 5},
            replace_todo_section(
                readme2["content"], "## 当前待办\n\n- [x] 本轮已完成项"
            ),
        )

        console = Console(width=140, record=True)
        console.print(build_mid_panel(proj, proj.read_manifest()))
        text = console.export_text()

        assert "本轮已完成项" in text
        assert "旧轮次遗留项" not in text      # 旧轮次不混进本轮列表
        assert "旧轮次未完成项" in text        # 但会提示存在历史残留
