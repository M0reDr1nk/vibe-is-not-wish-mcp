"""Contracts added in L3 v0.14 (descent-13): fingerprint prerequisite,
triage coverage, decision states, heal ordering, tool catalog."""

import json
import re
import shutil
from pathlib import Path

import pytest

import vinw.server as server
from vinw.store.project import Project, replace_todo_section
from vinw.workflow.consistency_gate import ConsistencyGate
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
from vinw.workflow.state_machine import ConsistencyGateError, WorkflowEngine
from vinw.workflow.triage import AuditTriage, TriageError


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "contract-proj"
    p = Project.init(root, "contract-proj", "")
    (root / "main.py").write_text("def main():\n    return 0\n")
    p.write_document("L3-方案细化", "api-design.md", "| 接口 |\n|------|\n| `main` |\n")
    p.write_document("L3-方案细化", "design-doc.md", "# 设计\n")
    for layer in ("L4-编码实现", "L5-测试验证"):
        r = p.read_layer_readme(layer)
        p.write_layer_readme(
            layer,
            {**r, "todo_descent": 1},
            replace_todo_section(r["content"], "## 当前待办\n\n- [x] done"),
        )
    yield p
    shutil.rmtree(root.parent, ignore_errors=True)


def store_llm(proj, overall="warning", findings=None):
    gate = ConsistencyGate(proj)
    fp = gate.current_fingerprint()
    return LLMConsistencyAuditor(proj).store_report(
        {"overall": overall, "inconsistencies": findings or [], "matched": []},
        descent=proj.read_manifest().get("current_descent", 1),
        design_digest=fp["design_hash"],
        hashes=fp["file_hashes"],
        kind="llm",
        auditor="reviewer",
    )


class TestFingerprintPrerequisite:
    """INC-005: a verdict only counts for the code it was produced on."""

    def test_satisfied_requires_matching_fingerprint(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        store_llm(proj, overall="passed")

        assert gate.llm_status()["satisfied"] is True

        (proj.root / "main.py").write_text("def main():\n    return 42\n")
        status = gate.llm_status()
        assert status["present"] is True
        assert status["matches_current"] is False
        assert status["satisfied"] is False

    def test_descend_blocked_when_verdict_is_stale(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        store_llm(proj, overall="passed")
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L4-编码实现"
        proj.write_manifest(manifest)

        (proj.root / "main.py").write_text("def main():\n    return 7\n")

        from vinw.workflow.state_machine import LLMAuditRequiredError

        with pytest.raises((LLMAuditRequiredError, ConsistencyGateError)):
            WorkflowEngine(proj).descend("L5-测试验证", "stale verdict")


class TestTriageCoverage:
    """INC-009: partial triage must be rejected, not silently accepted."""

    def test_partial_triage_rejected(self, proj):
        store_llm(
            proj,
            findings=[{"id": "INC-1", "description": "a"}, {"id": "INC-2", "description": "b"}],
        )
        triage = AuditTriage(proj)
        with pytest.raises(TriageError) as exc:
            triage.store({"triage": [{"id": "INC-1", "classification": "ambiguous"}]})
        assert "INC-2" in str(exc.value)

    def test_full_coverage_accepted(self, proj):
        store_llm(
            proj,
            findings=[{"id": "INC-1", "description": "a"}, {"id": "INC-2", "description": "b"}],
        )
        result = AuditTriage(proj).store(
            {
                "triage": [
                    {"id": "INC-1", "classification": "impl_bug", "confidence": "high"},
                    {"id": "INC-2", "classification": "ambiguous", "confidence": "low"},
                ]
            }
        )
        assert result["total"] == 2


class TestDecisionStates:
    """GAP-005: five states, including resolved and untriaged routing."""

    def test_untriaged_escalates(self, proj):
        store_llm(proj, findings=[{"id": "INC-1", "description": "a"}])
        decision = AuditTriage(proj).decision()
        assert decision["decision"] == "escalate"
        assert decision["untriaged"] == ["INC-1"]

    def test_no_report_state(self, proj):
        assert AuditTriage(proj).decision()["decision"] == "no_llm_report"

    def test_design_findings_resolve_to_resolved_not_auto_fixable(self, proj):
        store_llm(proj, findings=[{"id": "INC-1", "description": "a"}])
        triage = AuditTriage(proj)
        triage.store(
            {"triage": [{"id": "INC-1", "classification": "design_gap", "confidence": "high"}]}
        )
        assert triage.decision()["decision"] == "escalate"

        triage.record_decision("INC-1", "fix_design", "已补设计")
        decision = triage.decision()
        assert decision["decision"] == "resolved"
        assert decision["design_followups"] == ["INC-1"]

    def test_impl_bug_decided_is_auto_fixable(self, proj):
        store_llm(proj, findings=[{"id": "INC-1", "description": "a"}])
        triage = AuditTriage(proj)
        triage.store(
            {"triage": [{"id": "INC-1", "classification": "impl_bug", "confidence": "high"}]}
        )
        triage.record_decision("INC-1", "fix_impl", "修了")
        assert triage.decision()["decision"] == "auto_fixable"


class TestHealOrdering:
    """INC-012: a rejected transition must not leave an auto-audit trail."""

    def test_rejected_baseline_leaves_no_auto_audit(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        # make the code inconsistent so the L4 gate (or heal) must fail
        (proj.root / "main.py").write_text("def renamed():\n    return 0\n")

        changelog_path = proj.vinw_dir / "changelog.md"
        before = changelog_path.read_text(encoding="utf-8")

        with pytest.raises(ConsistencyGateError):
            WorkflowEngine(proj).baseline("L4-编码实现", "should be rejected")

        after = changelog_path.read_text(encoding="utf-8")
        assert after.count("auto-audit") == before.count("auto-audit"), (
            "a rejected transition must not record auto-audit"
        )

    def test_successful_baseline_records_auto_audit_only_on_drift(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        (proj.root / "main.py").write_text("def main():\n    return 9\n")

        WorkflowEngine(proj).baseline("L5-测试验证", "ok")
        changelog = (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        assert "auto-audit" in changelog


class TestToolCatalog:
    """GAP-004: the design tool list must match the implementation."""

    def test_design_catalog_matches_registered_tools(self):
        import ast

        repo = Path(__file__).resolve().parents[1]
        server_src = (repo / "vinw" / "server.py").read_text(encoding="utf-8")
        tools = {
            n.name
            for n in ast.parse(server_src).body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("se_")
        }

        design = (repo / "vinw-design" / "L3-方案细化" / "api-design.md").read_text(
            encoding="utf-8"
        )
        section = design.split("## MCP 工具清单")[1].split("\n## ")[0]
        listed = set(re.findall(r"\| `(se_\w+)` \|", section))

        assert listed == tools, f"missing in design: {tools - listed}, stale: {listed - tools}"
        assert f"共 {len(tools)} 个" in design
