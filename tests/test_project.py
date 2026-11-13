"""Tests for vinw.store.project."""

import shutil
from pathlib import Path

import pytest

from vinw.store.project import Project, LAYERS


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project for testing."""
    root = tmp_path / "test-proj"
    proj = Project.init(root, "test-proj", "Test project")
    yield proj
    shutil.rmtree(root, ignore_errors=True)


class TestProjectInit:
    def test_directory_structure(self, temp_project):
        proj = temp_project
        assert proj.root.exists()
        assert proj.vinw_dir.exists()
        assert (proj.vinw_dir / "manifest.md").exists()
        assert (proj.vinw_dir / "changelog.md").exists()
        assert (proj.vinw_dir / "ascensions.md").exists()

    def test_all_layers_created(self, temp_project):
        proj = temp_project
        for layer in LAYERS:
            layer_dir = proj.get_layer_dir(layer)
            assert layer_dir.exists(), f"{layer} directory missing"
            assert (layer_dir / "README.md").exists(), f"{layer}/README.md missing"
            assert (layer_dir / ".baseline").exists(), f"{layer}/.baseline missing"

    def test_manifest_initial_state(self, temp_project):
        proj = temp_project
        manifest = proj.read_manifest()
        assert manifest["name"] == "test-proj"
        assert manifest["current_layer"] == "L1-需求拆解"
        assert manifest["current_descent"] == 1
        assert len(manifest["layer_states"]) == len(LAYERS)


class TestBaseline:
    def test_freeze_baseline(self, temp_project):
        proj = temp_project
        proj.write_document("L1-需求拆解", "proposals.md", "# Test content")
        path = proj.freeze_baseline("L1-需求拆解", "v001", "test baseline")
        assert path.exists()
        assert proj.list_baselines("L1-需求拆解") == ["v001"]

    def test_rollback_to_baseline(self, temp_project):
        proj = temp_project
        proj.write_document("L1-需求拆解", "proposals.md", "# Original")
        proj.freeze_baseline("L1-需求拆解", "v001", "freeze")
        # Modify README
        readme = proj.read_layer_readme("L1-需求拆解")
        proj.write_layer_readme("L1-需求拆解", readme, readme["content"] + "\n\nmodified")
        # Rollback
        proj.rollback_to_baseline("L1-需求拆解", "v001")
        rolled = proj.read_layer_readme("L1-需求拆解")
        assert rolled.get("rolled_back_from") == "v001"

    def test_baseline_versions_increment(self, temp_project):
        proj = temp_project
        proj.freeze_baseline("L1-需求拆解", "v001", "first")
        proj.freeze_baseline("L1-需求拆解", "v002", "second")
        assert proj.list_baselines("L1-需求拆解") == ["v001", "v002"]


class TestDocumentCRUD:
    def test_write_and_read(self, temp_project):
        proj = temp_project
        proj.write_document("L1-需求拆解", "test.md", "# Hello", doc_type="test")
        doc = proj.read_document("L1-需求拆解", "test.md")
        assert doc["content"] == "# Hello"
        assert doc["doc_type"] == "test"

    def test_read_nonexistent(self, temp_project):
        proj = temp_project
        with pytest.raises(FileNotFoundError):
            proj.read_document("L1-需求拆解", "nonexistent.md")


class TestTodoScanning:
    def test_get_todos(self, temp_project):
        proj = temp_project
        readme = proj.read_layer_readme("L1-需求拆解")
        content = readme["content"]
        content += "\n- [ ] Task A\n- [x] Task B\n"
        proj.write_layer_readme("L1-需求拆解", readme, content)
        todos = proj.get_todos()
        # Filter to only our added todos (templates have default todos)
        our_todos = [t for t in todos if t["text"] in ("Task A", "Task B")]
        assert len(our_todos) == 2
        assert our_todos[0]["text"] == "Task A"
        assert not our_todos[0]["done"]
        assert our_todos[1]["done"]


class TestChangelog:
    def test_changelog_append(self, temp_project):
        proj = temp_project
        from vinw.store.changelog import append_changelog_entry
        append_changelog_entry(
            proj.vinw_dir / "changelog.md",
            change_type="test",
            layer="L1-需求拆解",
            descent=1,
            scope="test",
            reason="test entry",
            before="before",
            after="after",
        )
        changelog = (proj.vinw_dir / "changelog.md").read_text()
        assert "chg-" in changelog
        assert "test entry" in changelog
