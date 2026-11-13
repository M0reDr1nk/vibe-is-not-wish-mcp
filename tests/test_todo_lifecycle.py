"""Tests for todo lifecycle, baseline guard, and confirmation purge (L3 v0.6)."""

import json
import shutil

import pytest

import vinw.server as server
from vinw.store.project import (
    Project,
    TODO_PLACEHOLDER,
    extract_todo_section,
    has_placeholder_todo,
    replace_todo_section,
)
from vinw.workflow.state_machine import WorkflowEngine


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "lifecycle"
    p = Project.init(root, "lifecycle", "todo lifecycle")
    yield p
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def active(proj):
    saved = server._active_project
    server._active_project = proj
    yield proj
    server._active_project = saved


class TestSectionHelpers:
    def test_extract_and_replace(self, proj):
        readme = proj.read_layer_readme("L1-需求拆解")
        content = replace_todo_section(readme["content"], "## 当前待办\n\n- [ ] Alpha")
        section = extract_todo_section(content)
        assert section == "## 当前待办\n\n- [ ] Alpha"
        assert "## 阶段小结" in content

    def test_extract_missing_returns_none(self):
        assert extract_todo_section("# Title\n\nbody") is None

    def test_replace_appends_when_missing(self):
        out = replace_todo_section("# Title\n", "## 当前待办\n\n- [x] X")
        assert "## 当前待办" in out

    def test_placeholder_detection(self, proj):
        readme = proj.read_layer_readme("L2-参考文献与方案搜证汇总")
        assert has_placeholder_todo(readme["content"]) is True
        cleaned = replace_todo_section(readme["content"], "## 当前待办\n\n- [x] done")
        assert has_placeholder_todo(cleaned) is False


class TestRollbackKeepsTodos:
    def test_rollback_preserves_live_todos(self, proj):
        engine = WorkflowEngine(proj)
        # Real todos, then baseline
        readme = proj.read_layer_readme("L1-需求拆解")
        proj.write_layer_readme(
            "L1-需求拆解",
            {**readme, "todo_descent": 1},
            replace_todo_section(readme["content"], "## 当前待办\n\n- [x] first round"),
        )
        engine.baseline("L1-需求拆解", "v001")

        # Advance todos past the baseline
        readme = proj.read_layer_readme("L1-需求拆解")
        proj.write_layer_readme(
            "L1-需求拆解",
            {**readme, "todo_descent": 4},
            replace_todo_section(readme["content"], "## 当前待办\n\n- [x] later work"),
        )

        # Rollback must keep the live todo list, not the frozen one
        proj.rollback_to_baseline("L1-需求拆解", "v001")
        after = proj.read_layer_readme("L1-需求拆解")
        assert "later work" in after["content"]
        assert "first round" not in after["content"]
        assert after["todo_descent"] == 4
        assert after["rolled_back_from"] == "v001"

    def test_rollback_without_live_readme_still_works(self, proj):
        engine = WorkflowEngine(proj)
        engine.baseline("L2-参考文献与方案搜证汇总", "test", force=True)
        (proj.get_layer_dir("L2-参考文献与方案搜证汇总") / "README.md").unlink()
        proj.rollback_to_baseline("L2-参考文献与方案搜证汇总", "v001")
        assert (proj.get_layer_dir("L2-参考文献与方案搜证汇总") / "README.md").exists()


class TestBaselinePlaceholderGuard:
    def test_baseline_refuses_on_placeholder(self, active):
        result = json.loads(server.se_baseline("L1-需求拆解"))
        assert "error" in result
        assert TODO_PLACEHOLDER in result["error"]
        assert proj_baselines(active, "L1-需求拆解") == []

    def test_force_bypasses_guard(self, active):
        result = json.loads(server.se_baseline("L1-需求拆解", force=True))
        assert result["version"] == "v001"

    def test_baseline_ok_after_todos_written(self, active):
        server.se_update_todo("L1-需求拆解", json.dumps([{"done": True, "text": "real"}]))
        result = json.loads(server.se_baseline("L1-需求拆解"))
        assert result["status"] == "baselined"


def proj_baselines(proj, layer):
    return proj.list_baselines(layer)


class TestPurgeConfirmations:
    def _project_advanced(self, proj, current_descent=3, pending=None):
        manifest = proj.read_manifest()
        manifest["current_descent"] = current_descent
        manifest["pending_confirmations"] = pending or []
        proj.write_manifest(manifest)

    def test_purges_older_non_blocking(self, active):
        self._project_advanced(
            active,
            3,
            [
                {"id": "cfm-old", "descent": 2, "blocking": False, "resolved_at": None},
                {"id": "cfm-block", "descent": 2, "blocking": True, "resolved_at": None},
                {"id": "cfm-now", "descent": 3, "blocking": False, "resolved_at": None},
            ],
        )
        result = json.loads(server.se_purge_confirmations())
        assert result["purged"] == 2
        assert set(result["ids"]) == {"cfm-old", "cfm-block"}

        manifest = active.read_manifest()
        by_id = {p["id"]: p for p in manifest["pending_confirmations"]}
        assert by_id["cfm-now"]["resolved_at"] is None
        assert by_id["cfm-old"]["resolution"] == "superseded"

    def test_purge_respects_cutoff(self, active):
        self._project_advanced(
            active,
            5,
            [{"id": "cfm-a", "descent": 2, "blocking": False, "resolved_at": None}],
        )
        result = json.loads(server.se_purge_confirmations(before_descent=2))
        assert result["purged"] == 1

    def test_purge_noop_when_nothing_stale(self, active):
        self._project_advanced(
            active,
            1,
            [{"id": "cfm-new", "descent": 1, "blocking": False, "resolved_at": None}],
        )
        result = json.loads(server.se_purge_confirmations())
        assert result["purged"] == 0


class TestCompleteProjectGuards:
    def _ready_project(self, proj):
        from vinw.store.project import LAYERS
        from vinw.workflow.consistency_gate import ConsistencyGate

        manifest = proj.read_manifest()
        manifest["current_layer"] = "L7-终验"
        manifest["layer_states"] = {
            layer: {"status": "baselined", "latest_baseline": "v001"}
            for layer in LAYERS[:-1]
        }
        manifest["layer_states"]["L7-终验"] = {"status": "in_progress"}
        proj.write_manifest(manifest)
        for layer in LAYERS:
            readme = proj.read_layer_readme(layer)
            proj.write_layer_readme(
                layer,
                readme,
                replace_todo_section(readme["content"], "## 当前待办\n\n- [x] done"),
            )
        ConsistencyGate(proj).ensure()  # completion requires a passing report

    def test_blocks_on_placeholder_todo(self, active):
        from vinw.store.project import LAYERS

        self._ready_project(active)
        readme = active.read_layer_readme(LAYERS[0])
        active.write_layer_readme(
            LAYERS[0],
            readme,
            replace_todo_section(readme["content"], f"## 当前待办\n\n{TODO_PLACEHOLDER}"),
        )
        result = json.loads(server.se_complete_project())
        assert "error" in result
        assert any("占位符" in d for d in result["details"])

    def test_success_purges_stale_non_blocking(self, active):
        self._ready_project(active)
        manifest = active.read_manifest()
        manifest["current_descent"] = 3
        manifest["pending_confirmations"] = [
            {"id": "cfm-stale", "descent": 1, "blocking": False, "resolved_at": None}
        ]
        active.write_manifest(manifest)

        from vinw.workflow.consistency_gate import ConsistencyGate

        ConsistencyGate(active).ensure()  # report must belong to descent 3

        result = json.loads(server.se_complete_project())
        assert result["status"] == "completed"
        assert result["purged_confirmations"] == ["cfm-stale"]

    def test_blocking_gate_still_blocks_completion(self, active):
        self._ready_project(active)
        manifest = active.read_manifest()
        manifest["current_descent"] = 3
        manifest["pending_confirmations"] = [
            {"id": "cfm-block", "descent": 3, "blocking": True, "resolved_at": None}
        ]
        active.write_manifest(manifest)

        result = json.loads(server.se_complete_project())
        assert "error" in result
        assert any("blocking" in d for d in result["details"])
