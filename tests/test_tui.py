"""Smoke tests for the TUI (headless via textual run_test)."""

import asyncio
import shutil

import pytest

from vinw.store.project import Project
from vinw.tui.app import SEApp


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
    """No-project path shows the warning panel instead of crashing."""
    app = SEApp(None)

    async def scenario(pilot):
        await pilot.pause()
        assert "No active project" in str(app.query_one("#top-content").content)

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
