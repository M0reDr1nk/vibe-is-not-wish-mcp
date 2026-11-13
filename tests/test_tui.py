"""Smoke tests for the TUI (headless via textual run_test)."""

import asyncio
import shutil

import pytest

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
