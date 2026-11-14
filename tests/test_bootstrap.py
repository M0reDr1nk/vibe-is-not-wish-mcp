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


class TestCompleteProject:
    def _project_at_l7(self, tmp_path, blocking_pending=False):
        """Craft a project whose manifest sits at L7 with L1-L6 baselined."""
        from vinw.store.project import LAYERS

        root = tmp_path / "done-proj"
        proj = Project.init(root, "done-proj", "completion test")
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L7-终验"
        manifest["layer_states"] = {
            layer: {"status": "baselined", "latest_baseline": "v001"}
            for layer in LAYERS[:-1]
        }
        manifest["layer_states"]["L7-终验"] = {"status": "in_progress"}
        if blocking_pending:
            manifest["pending_confirmations"] = [
                {"id": "cfm-x", "blocking": True, "resolved_at": None}
            ]
        proj.write_manifest(manifest)
        # Completion now requires real todo lists (placeholder guard, L3 v0.6)
        from vinw.store.project import replace_todo_section

        for layer in LAYERS:
            readme = proj.read_layer_readme(layer)
            proj.write_layer_readme(
                layer,
                readme,
                replace_todo_section(readme["content"], "## 当前待办\n\n- [x] done"),
            )
        # Completion requires a passing consistency report for this descent.
        # An empty code scan is an error now, so give the project real code.
        (proj.root / "main.py").write_text("def main():\n    return 0\n")
        from vinw.workflow.consistency_gate import ConsistencyGate

        ConsistencyGate(proj).ensure()
        # text+llm is the default policy: store a reviewer verdict as well
        from vinw.workflow.consistency_llm import LLMConsistencyAuditor

        gate = ConsistencyGate(proj)
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": [], "gaps": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            policy="text+llm",
            auditor="reviewer",
        )
        return proj

    def test_complete_success(self, tmp_path, clean_active_project):
        import json as _json

        proj = self._project_at_l7(tmp_path)
        server._active_project = proj
        result = _json.loads(server.se_complete_project())
        assert result["status"] == "completed"
        assert result["completed_at"]
        manifest = proj.read_manifest()
        assert manifest["layer_states"]["L7-终验"]["status"] == "completed"
        assert manifest["completed_at"] == result["completed_at"]
        readme = proj.read_layer_readme("L7-终验")
        assert readme["status"] == "completed"

    def test_complete_rejected_when_not_l7(self, tmp_path, clean_active_project):
        import json as _json

        root = tmp_path / "early"
        proj = Project.init(root, "early", "")
        server._active_project = proj
        result = _json.loads(server.se_complete_project())
        assert "error" in result
        assert "L7-终验" in result["details"][0]

    def test_complete_rejected_with_blocking_gate(self, tmp_path, clean_active_project):
        import json as _json

        proj = self._project_at_l7(tmp_path, blocking_pending=True)
        server._active_project = proj
        result = _json.loads(server.se_complete_project())
        assert "error" in result
        assert any("blocking" in d for d in result["details"])
        # State must be untouched
        assert proj.read_manifest()["layer_states"]["L7-终验"]["status"] == "in_progress"
