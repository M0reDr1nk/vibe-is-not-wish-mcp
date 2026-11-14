"""Tests for the layered audit contract (L3 v0.11 / descent-11)."""

import json
import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project
from vinw.workflow.consistency_gate import ConsistencyGate
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
from vinw.workflow.state_machine import (
    ConsistencyGateError,
    LLMAuditRequiredError,
    WorkflowEngine,
)


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "audit-proj"
    p = Project.init(root, "audit-proj", "audit policy")
    (root / "main.py").write_text("def main():\n    return 0\n")
    p.write_document("L3-方案细化", "api-design.md", "| `main` |\n")
    p.write_document("L3-方案细化", "design-doc.md", "# 设计\n")
    p.write_document("L4-编码实现", "implementation.md", "# impl\n")
    from vinw.store.project import replace_todo_section

    for layer in ("L4-编码实现",):
        r = p.read_layer_readme(layer)
        p.write_layer_readme(
            layer,
            {**r, "todo_descent": 1},
            replace_todo_section(r["content"], "## 当前待办\n\n- [x] 实现"),
        )
    yield p
    shutil.rmtree(root.parent, ignore_errors=True)


@pytest.fixture
def active(proj):
    saved, saved_reg = server._active_project, server._registry
    server._active_project = proj
    server._registry = None
    yield proj
    server._active_project, server._registry = saved, saved_reg


def set_policy(proj, policy):
    manifest = proj.read_manifest()
    manifest["consistency_policy"] = policy
    proj.write_manifest(manifest)


def store_llm(proj, overall="passed", auditor="reviewer", gaps=None, incs=None):
    gate = ConsistencyGate(proj)
    fp = gate.current_fingerprint()
    return LLMConsistencyAuditor(proj).store_report(
        {
            "overall": overall,
            "inconsistencies": incs or [],
            "matched": [],
            "gaps": gaps or [],
        },
        descent=proj.read_manifest().get("current_descent", 1),
        design_digest=fp["design_hash"],
        hashes=fp["file_hashes"],
        kind="llm",
        policy=proj.read_manifest().get("consistency_policy", "text+llm"),
        auditor=auditor,
    )


class TestPolicyGating:
    def test_text_policy_does_not_require_llm(self, proj):
        set_policy(proj, "text")
        status = ConsistencyGate(proj).llm_status()
        assert status["required"] is False
        assert status["satisfied"] is True

    def test_default_policy_requires_llm(self, proj):
        assert ConsistencyGate(proj).policy() == "text+llm"
        assert ConsistencyGate(proj).llm_status()["satisfied"] is False

    def test_llm_report_satisfies_policy(self, proj):
        store_llm(proj)
        status = ConsistencyGate(proj).llm_status()
        assert status["satisfied"] is True
        assert status["auditor"] == "reviewer"

    def test_text_report_does_not_satisfy_llm_requirement(self, proj):
        ConsistencyGate(proj).ensure()
        assert ConsistencyGate(proj).llm_status()["satisfied"] is False


class TestDescendGate:
    def _at_l4(self, proj):
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L4-编码实现"
        proj.write_manifest(manifest)

    def test_descend_blocked_without_llm(self, proj):
        self._at_l4(proj)
        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).descend("L5-测试验证", "need reviewer")

    def test_descend_allowed_after_llm_passed(self, proj):
        self._at_l4(proj)
        ConsistencyGate(proj).ensure()
        store_llm(proj)
        result = WorkflowEngine(proj).descend("L5-测试验证", "ok")
        assert result["to_layer"] == "L5-测试验证"

    def test_warning_verdict_routes_to_triage_not_rejection(self, proj):
        """A warning verdict is a provided audit; triage decides the gate."""
        self._at_l4(proj)
        ConsistencyGate(proj).ensure()
        store_llm(proj, overall="warning")  # no findings -> triage says clear
        result = WorkflowEngine(proj).descend("L5-测试验证", "warning but clear")
        assert result["to_layer"] == "L5-测试验证"

    def test_text_policy_skips_llm_requirement(self, proj):
        self._at_l4(proj)
        set_policy(proj, "text")
        ConsistencyGate(proj).ensure()
        result = WorkflowEngine(proj).descend("L5-测试验证", "text only")
        assert result["to_layer"] == "L5-测试验证"


class TestDiscrepancy:
    def test_discrepancy_detected(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()  # text passes here (main exists)
        # Force a warning-level text report on the same fingerprint
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {
                "overall": "warning",
                "inconsistencies": [{"id": "INC-001", "description": "x"}],
                "matched": [],
            },
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="text",
        )
        store_llm(proj, overall="passed")

        disc = ConsistencyGate(proj).discrepancy()
        assert disc is not None
        assert "提取器" in disc["reason"]

    def test_no_discrepancy_when_text_passes(self, proj):
        ConsistencyGate(proj).ensure()
        store_llm(proj)
        assert ConsistencyGate(proj).discrepancy() is None


class TestReportMetadata:
    def test_llm_report_records_auditor_and_kind(self, proj):
        path = store_llm(proj, auditor="reviewer")
        import frontmatter

        meta = frontmatter.load(path).metadata
        assert meta["kind"] == "llm"
        assert meta["auditor"] == "reviewer"
        assert meta["llm_verdict"] == "passed"
        assert meta["policy"] == "text+llm"

    def test_gaps_recorded(self, proj):
        path = store_llm(
            proj,
            overall="warning",
            gaps=[{"id": "GAP-001", "design_ref": "a.md:1", "missing": "test",
                   "description": "缺测试", "severity": "critical"}],
        )
        import frontmatter

        meta = frontmatter.load(path).metadata
        assert meta["gaps_count"] == 1

    def test_store_report_tool_marks_llm_kind(self, active):
        ConsistencyGate(active).ensure()
        result = json.loads(
            server.se_store_consistency_report(
                json.dumps({"overall": "passed", "inconsistencies": [], "matched": []}),
                auditor="reviewer",
                auditor_model="test-model",
            )
        )
        assert result["status"] == "stored"

        manifest = active.read_manifest()
        consistency = manifest["layer_states"]["L4-编码实现"]["consistency"]
        assert consistency["llm_verdict"] == "passed"
        assert consistency["llm_auditor"] == "reviewer"


class TestPromptV2:
    def test_prompt_has_gaps_and_inconsistency_sections(self, proj):
        result = LLMConsistencyAuditor(proj).audit()
        prompt = result["prompt"]
        assert "缺口清单" in prompt
        assert "实现一致性" in prompt
        assert "code_ref" in prompt
        assert "gaps" in prompt


class TestStrictPolicy:
    """strict differs from text+llm exactly at baseline (GAP-004)."""

    def _l4_with_todos(self, proj):
        from vinw.store.project import replace_todo_section

        r = proj.read_layer_readme("L4-编码实现")
        proj.write_layer_readme(
            "L4-编码实现",
            {**r, "todo_descent": 1},
            replace_todo_section(r["content"], "## 当前待办\n\n- [x] 实现"),
        )

    def test_strict_baseline_requires_llm(self, proj):
        self._l4_with_todos(proj)
        set_policy(proj, "strict")
        from vinw.workflow.state_machine import LLMAuditRequiredError

        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).baseline("L4-编码实现", "strict needs verdict")

    def test_strict_baseline_passes_with_llm(self, proj):
        self._l4_with_todos(proj)
        set_policy(proj, "strict")
        ConsistencyGate(proj).ensure()
        store_llm(proj)
        result = WorkflowEngine(proj).baseline("L4-编码实现", "strict ok")
        assert result["status"] == "baselined"

    def test_text_plus_llm_baseline_does_not_require_llm(self, proj):
        self._l4_with_todos(proj)
        set_policy(proj, "text+llm")
        result = WorkflowEngine(proj).baseline("L4-编码实现", "baseline only needs text")
        assert result["status"] == "baselined"
