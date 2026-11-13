"""Tests for VINW self-hosting bootstrap (vinw.server)."""

import json
import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project


@pytest.fixture
def clean_active_project():
    """Save/restore the module-level active project around each test."""
    saved = server._active_project
    yield
    server._active_project = saved


def _make_project(root) -> Project:
    return Project.init(root, root.name, "test")


class TestBootstrapLoader:
    def test_loads_vinw_design_subdir(self, tmp_path, monkeypatch, clean_active_project):
        repo = tmp_path / "repo"
        design = repo / "vinw-design"
        _make_project(design)
        monkeypatch.chdir(repo)
        proj = server._try_load_bootstrap_project()
        assert proj is not None
        assert proj.root == design.resolve()

    def test_loads_cwd_project(self, tmp_path, monkeypatch, clean_active_project):
        proj_dir = tmp_path / "plain-proj"
        _make_project(proj_dir)
        monkeypatch.chdir(proj_dir)
        proj = server._try_load_bootstrap_project()
        assert proj is not None
        assert proj.root == proj_dir.resolve()

    def test_prefers_vinw_design_over_cwd(self, tmp_path, monkeypatch, clean_active_project):
        repo = tmp_path / "repo"
        _make_project(repo)  # cwd itself is also a project
        design = repo / "vinw-design"
        _make_project(design)
        monkeypatch.chdir(repo)
        proj = server._try_load_bootstrap_project()
        assert proj.root == design.resolve()

    def test_no_project_returns_none(self, tmp_path, monkeypatch, clean_active_project):
        monkeypatch.chdir(tmp_path)
        assert server._try_load_bootstrap_project() is None


class TestInitProjectAdopt:
    def test_adopts_existing_project(self, tmp_path, clean_active_project):
        target = tmp_path / "existing"
        _make_project(target)
        result = json.loads(server.se_init_project(name="existing", path=str(tmp_path)))
        assert result["adopted"] is True
        assert result["project_id"] == str(target.resolve())
        assert server._active_project.root == target.resolve()

    def test_fresh_init_when_empty(self, tmp_path, clean_active_project):
        result = json.loads(server.se_init_project(name="fresh", path=str(tmp_path)))
        assert "adopted" not in result
        assert result["current_layer"] == "L1-需求拆解"
        assert (tmp_path / "fresh" / ".vinw" / "manifest.md").exists()

    def test_adopt_returns_actual_state(self, tmp_path, clean_active_project):
        target = tmp_path / "existing"
        proj = _make_project(target)
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L4-编码实现"
        manifest["current_descent"] = 3
        proj.write_manifest(manifest)
        result = json.loads(server.se_init_project(name="existing", path=str(tmp_path)))
        assert result["adopted"] is True
        assert result["current_layer"] == "L4-编码实现"
        assert result["current_descent"] == 3
