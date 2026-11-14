"""Tests for the consistency gate: freshness, enforcement, reuse (L3 v0.9)."""

import json
import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
from vinw.workflow.consistency_gate import (
    FRESH,
    MISSING,
    STALE_DESIGN,
    STALE_FILES,
    ConsistencyGate,
)
from vinw.workflow.state_machine import WorkflowEngine


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "gate-proj"
    p = Project.init(root, "gate-proj", "gate test")
    # Code lives next to the project; design doc + api doc exist from init
    pkg = root.parent / "code"
    pkg.mkdir(exist_ok=True)
    (pkg / "mod.py").write_text("def se_alpha():\n    pass\n")
    manifest = p.read_manifest()
    manifest["code_root"] = ".."
    p.write_manifest(manifest)
    p.write_document(
        "L3-方案细化",
        "api-design.md",
        "# 接口\n\n| 接口名 |\n|--------|\n| `se_alpha` |\n",
    )
    p.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n初次设计\n")

    from vinw.store.project import replace_todo_section

    readme = p.read_layer_readme("L4-编码实现")
    p.write_layer_readme(
        "L4-编码实现",
        {**readme, "todo_descent": 1},
        replace_todo_section(readme["content"], "## 当前待办\n\n- [x] 实现完成"),
    )
    yield p
    shutil.rmtree(root.parent, ignore_errors=True)


@pytest.fixture
def active(proj):
    saved = server._active_project
    saved_reg = server._registry
    server._active_project = proj
    server._registry = None
    yield proj
    server._active_project = saved
    server._registry = saved_reg


class TestFreshness:
    def test_missing_when_no_report(self, proj):
        assert ConsistencyGate(proj).freshness(["code"])["state"] == MISSING

    def test_fresh_after_ensure(self, proj):
        gate = ConsistencyGate(proj)
        first = gate.ensure(scope=["code"])
        assert first["reused"] is False
        second = gate.ensure(scope=["code"])
        assert second["reused"] is True
        assert gate.freshness(["code"])["state"] == FRESH

    def test_stale_files_when_code_changes(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure(scope=["code"])
        (proj.root.parent / "code" / "mod.py").write_text(
            "def se_alpha():\n    pass\n\ndef se_beta():\n    pass\n"
        )
        status = gate.freshness(["code"])
        assert status["state"] == STALE_FILES
        assert any(p.endswith("mod.py") for p in status["changed"])

    def test_stale_design_when_design_changes(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure(scope=["code"])
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改过的设计\n")
        assert gate.freshness(["code"])["state"] == STALE_DESIGN

    def test_added_and_removed_files_detected(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure(scope=["code"])
        pkg = proj.root.parent / "code"
        (pkg / "extra.py").write_text("def se_gamma():\n    pass\n")
        status = gate.freshness(["code"])
        assert status["state"] == STALE_FILES
        assert any(p.endswith("extra.py") for p in status["changed"])


class TestEnforcement:
    def test_baseline_l4_autochecks_and_passes(self, proj):
        engine = WorkflowEngine(proj)
        # api-design declares se_alpha which exists -> passes
        result = engine.baseline("L4-编码实现", "with gate")
        assert result["status"] == "baselined"
        # Manifest records the check state
        consistency = proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"]
        assert consistency["overall"] == "passed"

    def test_baseline_l4_blocks_on_failure(self, proj):
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "# 接口\n\n| 接口名 |\n|--------|\n| `se_missing_symbol` |\n",
        )
        engine = WorkflowEngine(proj)
        with pytest.raises(ValueError) as exc:
            engine.baseline("L4-编码实现", "should fail")
        assert "一致性" in str(exc.value)

    def test_baseline_l4_force_skips_gate(self, proj):
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "# 接口\n\n| 接口名 |\n|--------|\n| `se_missing_symbol` |\n",
        )
        result = WorkflowEngine(proj).baseline("L4-编码实现", "forced", force=True)
        assert result["status"] == "baselined"

    def test_descend_from_l4_regates(self, proj):
        engine = WorkflowEngine(proj)
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L4-编码实现"
        proj.write_manifest(manifest)

        # Code drifts after the passing check -> descend must re-check and fail
        engine.baseline("L4-编码实现", "ok")
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "# 接口\n\n| 接口名 |\n|--------|\n| `se_nope` |\n",
        )
        with pytest.raises(ValueError):
            engine.descend("L5-测试验证", "should be gated")


class TestReuse:
    def test_llm_check_reuses_only_with_matching_verdict(self, active):
        server.se_check_consistency(code_scope='["code"]', method="text")
        ConsistencyGate(active).ensure(scope=["code"])

        # no LLM verdict yet -> a prompt is returned instead of 'reused'
        result = json.loads(
            server.se_check_consistency(code_scope='["code"]', method="llm")
        )
        assert result.get("status") == "prompt_ready"

        # store a matching verdict, then it may be reused
        gate = ConsistencyGate(active)
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(active).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=active.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        reused = json.loads(
            server.se_check_consistency(code_scope='["code"]', method="llm")
        )
        assert reused["reused"] is True
        assert reused["overall"] == "passed"

    def test_ignore_fresh_forces_prompt(self, active):
        gate = ConsistencyGate(active)
        gate.ensure(scope=["code"])
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(active).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=active.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        result = json.loads(
            server.se_check_consistency(
                code_scope='["code"]', method="llm", ignore_fresh=True
            )
        )
        assert result.get("status") == "prompt_ready"

    def test_llm_check_runs_when_stale(self, active):
        ConsistencyGate(active).ensure(scope=["code"])
        (active.root.parent / "code" / "mod.py").write_text(
            "def se_alpha():\n    pass\n# edit\n"
        )

        result = json.loads(
            server.se_check_consistency(code_scope='["code"]', method="llm")
        )
        assert result.get("status") == "prompt_ready"


class TestPendingPresentation:
    def test_gates_split_by_blocking(self, active):
        server.se_require_confirmation("interface-design", "设计评审", blocking=None)
        server.se_require_confirmation("test-results", "测试知会", blocking=None)

        payload = json.loads(server.se_get_project())
        assert [g["item_type"] for g in payload["blocking_pending"]] == ["interface-design"]
        assert [g["item_type"] for g in payload["pending_review"]] == ["test-results"]

    def test_design_gates_default_to_blocking(self, active):
        result = json.loads(
            server.se_require_confirmation("requirement-decomposition", "需求评审")
        )
        manifest = active.read_manifest()
        gate = next(
            p for p in manifest["pending_confirmations"] if p["id"] == result["confirmation_id"]
        )
        assert gate["blocking"] is True

    def test_next_steps_lists_awaiting_review(self, active):
        server.se_require_confirmation("test-results", "知会", blocking=False)
        steps = json.loads(server.se_get_next_steps())
        assert any(g["item_type"] == "test-results" for g in steps["awaiting_review"])
