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
        async with app.run_test() as pilot:
            await coro_fn(pilot)

    asyncio.run(runner())


def test_tui_renders_with_project(proj):
    """Full refresh_ui render path must not raise (regression: Columns + Text TypeError)."""
    app = SEApp(str(proj.root))

    async def scenario(pilot):
        await pilot.pause()
        top = app.query_one("#top-panel")
        mid = app.query_one("#mid-panel")
        bottom = app.query_one("#bottom-panel")
        assert top.content is not None
        assert mid.content is not None
        assert bottom.content is not None

    _run(app, scenario)


def test_tui_renders_without_project():
    """No-project path shows the warning panel instead of crashing."""
    app = SEApp(None)

    async def scenario(pilot):
        await pilot.pause()
        top = app.query_one("#top-panel")
        assert "No active project" in str(top.content)

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
        top = app.query_one("#top-panel")
        assert top.content is not None

    _run(app, scenario)


def test_tui_survives_transient_file_error(proj):
    """A mid-rewrite/corrupt manifest must not kill the refresh loop."""
    app = SEApp(str(proj.root))

    async def scenario(pilot):
        await pilot.pause()
        # Remove the manifest to simulate a transient read during rewrite
        (proj.root / ".vinw" / "manifest.md").unlink()
        app.refresh_ui()  # must not raise
        await pilot.pause()
        bottom = app.query_one("#bottom-panel")
        panel = bottom.content
        assert "刷新出错" in str(getattr(panel, "renderable", panel))

    _run(app, scenario)
