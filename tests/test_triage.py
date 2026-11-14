"""Tests for audit triage: classification, routing, decisions, gate wiring."""

import json
import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project, replace_todo_section
from vinw.workflow.consistency_gate import ConsistencyGate
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
from vinw.workflow.state_machine import AuditEscalationError, WorkflowEngine
from vinw.workflow.triage import AuditTriage, TriageError, normalize_finding, requires_human


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "triage-proj"
    p = Project.init(root, "triage-proj", "triage")
    (root / "main.py").write_text("def main():\n    return 0\n")
    p.write_document("L3-方案细化", "api-design.md", "| 接口 |\n|------|\n| `main` |\n")
    p.write_document("L3-方案细化", "design-doc.md", "# 设计\n")
    r = p.read_layer_readme("L4-编码实现")
    p.write_layer_readme(
        "L4-编码实现",
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


def store_llm(proj, findings=None, overall="warning"):
    gate = ConsistencyGate(proj)
    fp = gate.current_fingerprint()
    return LLMConsistencyAuditor(proj).store_report(
        {
            "overall": overall,
            "inconsistencies": findings or [],
            "matched": [],
            "gaps": [],
        },
        descent=proj.read_manifest().get("current_descent", 1),
        design_digest=fp["design_hash"],
        hashes=fp["file_hashes"],
        kind="llm",
        policy="text+llm",
        auditor="reviewer",
    )


class TestNormalization:
    def test_unknown_classification_becomes_ambiguous(self):
        f = normalize_finding({"id": "A", "classification": "wtf", "confidence": "high"})
        assert f["classification"] == "ambiguous"

    def test_missing_confidence_becomes_low(self):
        f = normalize_finding({"id": "A", "classification": "impl_bug"})
        assert f["confidence"] == "low"

    def test_only_high_confidence_impl_bug_is_auto(self):
        auto = normalize_finding({"id": "A", "classification": "impl_bug", "confidence": "high"})
        human = normalize_finding({"id": "B", "classification": "impl_bug", "confidence": "medium"})
        assert requires_human(auto) is False
        assert requires_human(human) is True

    def test_design_classifications_need_human(self):
        for cls in ("design_bug", "design_gap", "ambiguous"):
            f = normalize_finding({"id": "x", "classification": cls, "confidence": "high"})
            assert requires_human(f) is True


class TestStoreAndDecision:
    def test_store_requires_llm_report(self, proj):
        with pytest.raises(TriageError):
            AuditTriage(proj).store({"triage": []})

    def test_store_and_read(self, proj):
        store_llm(proj, [{"id": "INC-001", "description": "x"}])
        result = AuditTriage(proj).store(
            {"triage": [{"id": "INC-001", "classification": "impl_bug",
                         "confidence": "high", "recommendation": "修实现"}]}
        )
        assert result["total"] == 1
        findings = AuditTriage(proj).findings()
        assert findings[0]["classification"] == "impl_bug"

    def test_decision_escalates_for_design_bug(self, proj):
        store_llm(proj, [{"id": "INC-001"}])
        AuditTriage(proj).store(
            {"triage": [{"id": "INC-001", "classification": "design_bug",
                         "confidence": "high", "difference": "d", "analysis": "a",
                         "recommendation": "r", "impact": "i"}]}
        )
        decision = AuditTriage(proj).decision()
        assert decision["decision"] == "escalate"
        assert decision["escalations"][0]["id"] == "INC-001"
        assert decision["escalations"][0]["difference"] == "d"

    def test_decision_auto_fix_pending_for_open_impl_bug(self, proj):
        store_llm(proj, [{"id": "INC-001"}])
        AuditTriage(proj).store(
            {"triage": [{"id": "INC-001", "classification": "impl_bug",
                         "confidence": "high", "recommendation": "修"}]}
        )
        assert AuditTriage(proj).decision()["decision"] == "auto_fix_pending"

    def test_decision_clear_when_all_fixed(self, proj):
        store_llm(proj, [{"id": "INC-001"}])
        triage = AuditTriage(proj)
        triage.store(
            {"triage": [{"id": "INC-001", "classification": "impl_bug", "confidence": "high"}]}
        )
        triage.record_decision("INC-001", "fix_impl", "已修")
        assert triage.decision()["decision"] == "auto_fixable"

    def test_decision_clear_without_findings(self, proj):
        store_llm(proj)
        assert AuditTriage(proj).decision()["decision"] == "clear"

    def test_record_decision_validates(self, proj):
        store_llm(proj, [{"id": "INC-001"}])
        AuditTriage(proj).store({"triage": [{"id": "INC-001"}]})
        triage = AuditTriage(proj)
        with pytest.raises(TriageError):
            triage.record_decision("INC-001", "nonsense")
        with pytest.raises(TriageError):
            triage.record_decision("missing-id", "fix_impl")

    def test_defer_keeps_open(self, proj):
        store_llm(proj, [{"id": "INC-001"}])
        triage = AuditTriage(proj)
        triage.store({"triage": [{"id": "INC-001", "classification": "ambiguous"}]})
        triage.record_decision("INC-001", "defer", "待下轮")
        assert triage.findings()[0]["status"] == "open"
        assert triage.decision()["decision"] == "escalate"


class TestGateIntegration:
    def _at_l4(self, proj):
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L4-编码实现"
        proj.write_manifest(manifest)

    def test_descend_blocked_on_escalation(self, proj):
        self._at_l4(proj)
        ConsistencyGate(proj).ensure()
        store_llm(proj, [{"id": "INC-001"}])
        AuditTriage(proj).store(
            {"triage": [{"id": "INC-001", "classification": "design_gap",
                         "confidence": "high"}]}
        )
        with pytest.raises(AuditEscalationError):
            WorkflowEngine(proj).descend("L5-测试验证", "needs decision")

    def test_descend_passes_after_decisions(self, proj):
        self._at_l4(proj)
        ConsistencyGate(proj).ensure()
        store_llm(proj, [{"id": "INC-001"}])
        triage = AuditTriage(proj)
        triage.store(
            {"triage": [{"id": "INC-001", "classification": "impl_bug", "confidence": "high"}]}
        )
        triage.record_decision("INC-001", "fix_impl", "已修实现")
        result = WorkflowEngine(proj).descend("L5-测试验证", "all clear")
        assert result["to_layer"] == "L5-测试验证"


class TestTools:
    def test_triage_prompt_lists_findings(self, active):
        store_llm(active, [{"id": "INC-001"}])
        AuditTriage(active).store({"triage": [{"id": "INC-001", "classification": "ambiguous"}]})
        payload = json.loads(server.se_triage_prompt())
        assert "design_bug" in payload["instructions"]
        assert payload["findings"][0]["id"] == "INC-001"

    def test_store_triage_tool(self, active):
        store_llm(active, [{"id": "INC-1"}])
        result = json.loads(
            server.se_store_triage(
                json.dumps({"triage": [{"id": "INC-1", "classification": "impl_bug",
                                        "confidence": "high"}]})
            )
        )
        assert result["total"] == 1

    def test_get_escalations_tool(self, active):
        store_llm(active, [{"id": "INC-1"}])
        AuditTriage(active).store(
            {"triage": [{"id": "INC-1", "classification": "design_bug",
                         "confidence": "medium", "difference": "d", "analysis": "a",
                         "recommendation": "r", "impact": "i"}]}
        )
        payload = json.loads(server.se_get_escalations())
        assert payload["count"] == 1
        assert payload["escalations"][0]["recommendation"] == "r"

    def test_record_decision_tool(self, active):
        store_llm(active, [{"id": "INC-1"}])
        AuditTriage(active).store({"triage": [{"id": "INC-1", "classification": "ambiguous"}]})
        result = json.loads(
            server.se_record_triage_decision("INC-1", "accept_as_is", "可接受")
        )
        assert result["status"] == "accepted"
        assert json.loads(server.se_get_escalations())["count"] == 0
