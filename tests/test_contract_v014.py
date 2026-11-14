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
        # code-only change is refused (design lag); move both to trigger a heal
        (proj.root / "main.py").write_text("def main():\n    return 9\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n同步\n")

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


class TestDesignLagEnforcement:
    """GAP-001: §9 says design lag must be refused, not just displayed."""

    def test_baseline_refuses_code_only_change(self, proj):
        from vinw.workflow.state_machine import DesignLagError

        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("def main():\n    return 5\n")
        with pytest.raises(DesignLagError):
            WorkflowEngine(proj).baseline("L5-测试验证", "should refuse")

    def test_descend_refuses_code_only_change(self, proj):
        from vinw.workflow.state_machine import DesignLagError

        ConsistencyGate(proj).ensure()
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L2-参考文献与方案搜证汇总"
        proj.write_manifest(manifest)
        (proj.root / "main.py").write_text("def main():\n    return 6\n")
        with pytest.raises(DesignLagError):
            WorkflowEngine(proj).descend("L3-方案细化", "should refuse")

    def test_complete_refuses_code_only_change(self, proj):
        from vinw.store.project import LAYERS

        # completion also requires real todo lists on every layer
        for layer in LAYERS:
            readme = proj.read_layer_readme(layer)
            proj.write_layer_readme(
                layer,
                readme,
                replace_todo_section(readme["content"], "## 当前待办\n\n- [x] done"),
            )
        ConsistencyGate(proj).ensure()
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L7-终验"
        audited = manifest["layer_states"].get("L4-编码实现", {}).get("consistency")
        manifest["layer_states"] = {
            layer: {"status": "baselined", "latest_baseline": "v001"}
            for layer in LAYERS[:-1]
        }
        # keep the audited fingerprint so drift detection has a baseline
        manifest["layer_states"]["L4-编码实现"]["consistency"] = audited
        manifest["layer_states"]["L7-终验"] = {"status": "in_progress"}
        proj.write_manifest(manifest)

        (proj.root / "main.py").write_text("def main():\n    return 8\n")
        saved = server._active_project
        server._active_project = proj
        try:
            result = json.loads(server.se_complete_project())
        finally:
            server._active_project = saved
        assert "error" in result
        details = " ".join(result.get("details", []))
        assert "设计" in details or "漂移" in details


class TestAuditLogDiscipline:
    """GAP-002: only a successful re-audit may log auto-audit."""

    def _auto_audit_count(self, proj):
        changelog = (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        return changelog.count("auto-audit")

    def test_config_error_writes_no_auto_audit(self, tmp_path):
        root = tmp_path / "nocode-log"
        proj = Project.init(root, "nocode-log", "")
        manifest = proj.read_manifest()
        manifest["layer_states"] = {
            "L4-编码实现": {"status": "baselined", "consistency": {"code_fingerprint": "x"}}
        }
        proj.write_manifest(manifest)

        before = self._auto_audit_count(proj)
        WorkflowEngine(proj).heal_drift("test")
        assert self._auto_audit_count(proj) == before

    def test_failed_reaudit_writes_no_auto_audit(self, proj):
        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("def renamed_away():\n    return 0\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n同步\n")

        before = self._auto_audit_count(proj)
        with pytest.raises(Exception):
            WorkflowEngine(proj).heal_drift("test")
        assert self._auto_audit_count(proj) == before


class TestAmbiguousRoutedToResolved:
    """INC-006: ambiguous needs design follow-up, not 'auto fixable'."""

    def test_ambiguous_accepted_is_resolved(self, proj):
        store_llm(proj, findings=[{"id": "INC-1", "description": "a"}])
        triage = AuditTriage(proj)
        triage.store(
            {"triage": [{"id": "INC-1", "classification": "ambiguous", "confidence": "medium"}]}
        )
        triage.record_decision("INC-1", "accept_as_is", "可接受")
        decision = triage.decision()
        assert decision["decision"] == "resolved"
        assert "INC-1" in decision["design_followups"]


class TestStateInvariants:
    """reviewer4: descend must not leave two layers in_progress."""

    def _in_progress(self, proj):
        states = proj.read_manifest()["layer_states"]
        return [l for l, s in states.items() if s.get("status") == "in_progress"]

    def test_descend_from_unfrozen_layer_keeps_single_in_progress(self, proj):
        WorkflowEngine(proj).descend("L2-参考文献与方案搜证汇总", "move on")
        layers = self._in_progress(proj)
        assert len(layers) == 1
        assert layers[0] == "L2-参考文献与方案搜证汇总"
        # the abandoned layer is reset, not left 'in progress'
        assert proj.read_manifest()["layer_states"]["L1-需求拆解"]["status"] == "pending"

    def test_completed_only_on_l7(self, proj):
        from vinw.store.project import LAYERS

        for layer in LAYERS:
            readme = proj.read_layer_readme(layer)
            proj.write_layer_readme(
                layer,
                readme,
                replace_todo_section(readme["content"], "## 当前待办\n\n- [x] done"),
            )
        ConsistencyGate(proj).ensure()
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L7-终验"
        audited = manifest["layer_states"].get("L4-编码实现", {}).get("consistency")
        manifest["layer_states"] = {
            layer: {"status": "baselined", "latest_baseline": "v001"}
            for layer in LAYERS[:-1]
        }
        manifest["layer_states"]["L4-编码实现"]["consistency"] = audited
        manifest["layer_states"]["L7-终验"] = {"status": "in_progress"}
        proj.write_manifest(manifest)

        saved = server._active_project
        server._active_project = proj
        try:
            json.loads(server.se_complete_project())
        finally:
            server._active_project = saved

        states = proj.read_manifest()["layer_states"]
        completed = [l for l, s in states.items() if s.get("status") == "completed"]
        # completion may be refused for other reasons (e.g. missing LLM verdict),
        # but no layer other than L7 may ever be 'completed'
        assert set(completed) <= {"L7-终验"}


class TestRepairSyncsReadmes:
    """GAP-001: repair must not leave the README mirror behind."""

    def test_repair_mirrors_and_clears_markers(self, proj):
        import frontmatter

        engine = WorkflowEngine(proj)
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")

        # simulate old-bug state: lower layer left baselined, manifest dirty
        manifest = proj.read_manifest()
        manifest["layer_states"]["L2-参考文献与方案搜证汇总"]["status"] = "baselined"
        manifest["layer_states"]["L2-参考文献与方案搜证汇总"]["superseded_by"] = "asc-001"
        manifest["current_layer"] = "L1-需求拆解"
        proj.write_manifest(manifest)

        engine.repair_ascend_state()

        states = proj.read_manifest()["layer_states"]
        assert states["L2-参考文献与方案搜证汇总"]["status"] == "superseded"
        assert "superseded_at" not in states["L1-需求拆解"]
        readme = frontmatter.load(proj.get_layer_dir("L2-参考文献与方案搜证汇总") / "README.md")
        assert readme.metadata["status"] == "superseded"

    def test_unknown_ascent_id_raises(self, proj):
        engine = WorkflowEngine(proj)
        engine.baseline("L1-需求拆解", "t", force=True)
        engine.descend("L2-参考文献与方案搜证汇总")
        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")

        with pytest.raises(ValueError):
            engine.repair_ascend_state("asc-999")


class TestAnonymousFindingsCoverage:
    """GAP-003: ids synthesised by findings() must match store()'s expectation."""

    def test_report_without_ids_can_be_triaged(self, proj):
        store_llm(proj, findings=[{"description": "no id here"}, {"description": "nor here"}])
        triage = AuditTriage(proj)
        ids = [f["id"] for f in triage.findings()]
        assert ids == ["INC-001", "INC-002"]

        result = triage.store(
            {
                "triage": [
                    {"id": "INC-001", "classification": "impl_bug", "confidence": "high"},
                    {"id": "INC-002", "classification": "ambiguous", "confidence": "low"},
                ]
            }
        )
        assert result["total"] == 2


class TestBaselineMetadataMirror:
    """GAP-005: README must carry the current baseline version."""

    def test_readme_baseline_version_matches_manifest(self, proj):
        import frontmatter

        engine = WorkflowEngine(proj)
        engine.baseline("L1-需求拆解", "t", force=True)

        manifest_state = proj.read_manifest()["layer_states"]["L1-需求拆解"]
        readme = frontmatter.load(proj.get_layer_dir("L1-需求拆解") / "README.md")
        assert readme.metadata["baseline_version"] == manifest_state["latest_baseline"]
        assert readme.metadata["baselined_at"] == manifest_state["baselined_at"]


class TestReviewer5Regressions:
    """Final-review findings: convergence, key names, extensions, aliases."""

    def test_heal_converges_when_report_is_fresh(self, proj):
        """INC-001: ensure() reusing a fresh report must still re-anchor state."""
        from vinw.workflow.consistency_llm import LLMConsistencyAuditor

        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("def main():\n    return 3\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")

        gate = ConsistencyGate(proj)
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        assert gate.freshness()["state"] == "fresh"

        WorkflowEngine(proj).heal_drift("test")

        from vinw.workflow.drift import detect_drift

        assert detect_drift(proj)["state"] == "clean"

    def test_llm_state_uses_descent_key(self, proj):
        """INC-004: record_llm_state wrote `descend`, nobody reads it."""
        import frontmatter

        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        path = LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        gate.record_llm_state(frontmatter.load(path).metadata)

        consistency = proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"]
        assert consistency.get("descent") is not None
        assert "descend" not in consistency

    def test_triage_accepts_finding_id_alias(self, proj):
        """INC-005: store() only honoured `id`, rejecting finding_id payloads."""
        store_llm(proj, findings=[{"id": "GAP-9", "description": "x"}])
        result = AuditTriage(proj).store(
            {
                "triage": [
                    {"finding_id": "GAP-9", "classification": "impl_bug", "confidence": "high"}
                ]
            }
        )
        assert result["total"] == 1

    def test_extra_finding_requires_valid_verdict(self, proj):
        from vinw.workflow.triage import TriageError

        store_llm(proj, findings=[{"id": "INC-1", "description": "x"}])
        with pytest.raises(TriageError):
            AuditTriage(proj).store(
                {
                    "triage": [
                        {"id": "INC-1", "classification": "impl_bug", "confidence": "high"},
                        {"id": "EXTRA-1", "classification": "nonsense"},
                    ]
                }
            )

    def test_fingerprint_honours_code_extensions(self, proj):
        """INC-006: fingerprints ignored manifest.code_extensions."""
        manifest = proj.read_manifest()
        manifest["code_extensions"] = [".c"]  # main.py is out of scope now
        proj.write_manifest(manifest)

        gate = ConsistencyGate(proj)
        before = gate.current_fingerprint()["code_fingerprint"]
        (proj.root / "main.py").write_text("def main():\n    return 99\n")
        assert gate.current_fingerprint()["code_fingerprint"] == before

    def test_invariants_hold_across_transitions(self, proj):
        from vinw.store.project import LAYERS, replace_todo_section

        engine = WorkflowEngine(proj)

        def in_progress():
            states = proj.read_manifest()["layer_states"]
            return [l for l, s in states.items() if s.get("status") == "in_progress"]

        engine.baseline("L1-需求拆解", "t", force=True)
        # after freezing the current layer there is no in_progress layer
        assert in_progress() == []

        engine.descend("L2-参考文献与方案搜证汇总")
        assert in_progress() == ["L2-参考文献与方案搜证汇总"]

        engine.baseline("L2-参考文献与方案搜证汇总", "t", force=True)
        engine.ascend("L2-参考文献与方案搜证汇总", "L1-需求拆解", "v001", "t")
        states = proj.read_manifest()["layer_states"]
        assert in_progress() == ["L1-需求拆解"]
        for layer in LAYERS[1:]:
            state = states.get(layer, {})
            if state.get("status") == "superseded":
                assert state.get("superseded_by"), layer
