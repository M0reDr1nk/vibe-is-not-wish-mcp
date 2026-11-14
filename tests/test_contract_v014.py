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

        from vinw.workflow.state_machine import DesignLagError, LLMAuditRequiredError

        with pytest.raises((ConsistencyGateError, LLMAuditRequiredError, DesignLagError)):
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

        # v0.15: after drift, a matching verdict is required before any
        # transition may proceed
        fp = ConsistencyGate(proj).current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )

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
        # the LLM verdict is fresh for the llm path ...
        assert gate.freshness(kind="llm")["state"] == "fresh"

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


class TestVerdictInvalidatedByDesignChange:
    """A verdict is only valid for the design text it reviewed.

    Without this, a stage-end text re-check could 'wash' drift clean and let
    the project advance on a verdict that never saw the new design.
    """

    def test_design_change_invalidates_satisfied(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        assert gate.llm_status()["satisfied"] is True

        # design text changes -> the old verdict no longer covers it
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n新约束\n")
        status = gate.llm_status()
        assert status["present"] is True
        assert status["matches_current"] is False
        assert status["satisfied"] is False

    def test_descend_blocked_after_design_change(self, proj):
        from vinw.workflow.state_machine import LLMAuditRequiredError

        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L4-编码实现"
        proj.write_manifest(manifest)

        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n新约束\n")

        with pytest.raises((LLMAuditRequiredError, Exception)):
            WorkflowEngine(proj).descend("L5-测试验证", "stale verdict")

    def test_code_fingerprint_excludes_design(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()  # establish an audited baseline first
        before = gate.current_fingerprint()["code_fingerprint"]
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")
        after = gate.current_fingerprint()
        assert after["code_fingerprint"] == before
        from vinw.workflow.drift import detect_drift

        assert detect_drift(proj)["state"] == "drifted"


class TestNoRetryBypass:
    """reviewer6: a rejected transition must not pass on a plain retry."""

    def _drift(self, proj):
        ConsistencyGate(proj).ensure()
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
        (proj.root / "main.py").write_text("def main():\n    return 4\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")

    def test_retry_without_verdict_still_blocked(self, proj):
        from vinw.workflow.state_machine import LLMAuditRequiredError

        self._drift(proj)
        for _ in range(2):
            with pytest.raises(LLMAuditRequiredError):
                WorkflowEngine(proj).baseline("L5-测试验证", "retry")

    def test_l4_baseline_also_requires_verdict(self, proj):
        from vinw.workflow.state_machine import LLMAuditRequiredError

        self._drift(proj)
        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).baseline("L4-编码实现", "L4 blind spot")

    def test_rejected_attempt_writes_no_auto_audit(self, proj):
        from vinw.workflow.state_machine import LLMAuditRequiredError

        changelog = proj.vinw_dir / "changelog.md"
        before = changelog.read_text(encoding="utf-8").count("auto-audit")

        self._drift(proj)
        before = changelog.read_text(encoding="utf-8").count("auto-audit")
        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).baseline("L5-测试验证", "rejected")

        assert changelog.read_text(encoding="utf-8").count("auto-audit") == before

    def test_report_without_design_hash_fails_closed(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest="",  # no design hash recorded
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )
        assert gate.llm_status()["matches_current"] is False

    def test_llm_report_anchors_fingerprint_without_manifest_state(self, proj):
        """GAP-004: review-then-record flows must still be drift-checked."""
        from vinw.workflow.drift import detect_drift

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
        import frontmatter

        gate.record_llm_state(frontmatter.load(path).metadata)
        consistency = proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"]
        assert consistency.get("code_fingerprint")
        assert consistency.get("design_hash")


class TestFailedRecheckDoesNotAnchor:
    """reviewer7 GAP-001 residue: a failing text re-check must not re-anchor."""

    def _setup(self, proj, policy="text"):
        manifest = proj.read_manifest()
        manifest["consistency_policy"] = policy
        proj.write_manifest(manifest)
        ConsistencyGate(proj).ensure()

    def test_retry_after_failed_text_check_still_blocked(self, proj):
        self._setup(proj)
        (proj.root / "main.py").write_text("def renamed():\n    return 0\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")

        from vinw.workflow.drift import detect_drift

        for _ in range(2):
            with pytest.raises(Exception):
                WorkflowEngine(proj).baseline("L5-测试验证", "retry")
            # the failed attempt must not make the tree look clean
            assert detect_drift(proj)["state"] != "clean"

    def test_failed_report_recorded_without_anchoring(self, proj):
        self._setup(proj)
        gate = ConsistencyGate(proj)
        anchored = proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"][
            "code_fingerprint"
        ]

        (proj.root / "main.py").write_text("def renamed():\n    return 0\n")
        result = gate.ensure()
        assert result["overall"] != "passed"

        consistency = proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"]
        assert consistency.get("last_failed_report")
        assert consistency["code_fingerprint"] == anchored  # unchanged


class TestL4DeferredAuditLog:
    """GAP-012: a rejected L4 baseline must not leave an auto-audit entry."""

    def test_placeholder_rejection_leaves_no_audit(self, proj):
        from vinw.workflow.state_machine import PlaceholderTodoError

        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("def main():\n    return 6\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")

        # L4 README starts with the template placeholder in a fresh project
        readme = proj.read_layer_readme("L4-编码实现")
        proj.write_layer_readme(
            "L4-编码实现",
            readme,
            replace_todo_section(readme["content"], "## 当前待办\n\n- [ ] 初始化本层工作"),
        )

        changelog = proj.vinw_dir / "changelog.md"
        before = changelog.read_text(encoding="utf-8").count("auto-audit")

        with pytest.raises(PlaceholderTodoError):
            WorkflowEngine(proj).baseline("L4-编码实现", "rejected")

        assert changelog.read_text(encoding="utf-8").count("auto-audit") == before


class TestForceIsVisible:
    """GAP-013: force must leave a trace in the changelog."""

    def test_forced_baseline_marks_reason(self, proj):
        WorkflowEngine(proj).baseline("L1-需求拆解", "forced for test", force=True)
        changelog = (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        assert "[force]" in changelog


class TestRejectedBaselineIsFullySideEffectFree:
    """reviewer8 INC-001: a rejected baseline must not even advance the anchor."""

    def test_placeholder_rejection_keeps_drift_state(self, proj):
        from vinw.workflow.drift import detect_drift
        from vinw.workflow.state_machine import PlaceholderTodoError

        manifest = proj.read_manifest()
        manifest["consistency_policy"] = "text"
        proj.write_manifest(manifest)
        ConsistencyGate(proj).ensure()

        (proj.root / "main.py").write_text("def main():\n    return 2\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")
        assert detect_drift(proj)["state"] != "clean"

        readme = proj.read_layer_readme("L4-编码实现")
        proj.write_layer_readme(
            "L4-编码实现",
            readme,
            replace_todo_section(readme["content"], "## 当前待办\n\n- [ ] 初始化本层工作"),
        )
        changelog = proj.vinw_dir / "changelog.md"
        before = changelog.read_text(encoding="utf-8").count("auto-audit")

        with pytest.raises(PlaceholderTodoError):
            WorkflowEngine(proj).baseline("L4-编码实现", "rejected")

        # nothing was written: drift unchanged, no audit entry
        assert detect_drift(proj)["state"] != "clean"
        assert changelog.read_text(encoding="utf-8").count("auto-audit") == before

    def test_successful_path_records_the_audit(self, proj):
        from vinw.workflow.drift import detect_drift

        manifest = proj.read_manifest()
        manifest["consistency_policy"] = "text"
        proj.write_manifest(manifest)
        ConsistencyGate(proj).ensure()

        (proj.root / "main.py").write_text("def main():\n    return 3\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")

        WorkflowEngine(proj).baseline("L4-编码实现", "ok")

        assert detect_drift(proj)["state"] == "clean"
        changelog = (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        assert "auto-audit" in changelog


class TestStrictRejectionIsSideEffectFree:
    """reviewer9: strict/triage rejections must also precede healing."""

    def test_strict_rejection_keeps_drift_and_log(self, proj):
        from vinw.workflow.drift import detect_drift
        from vinw.workflow.state_machine import LLMAuditRequiredError

        manifest = proj.read_manifest()
        manifest["consistency_policy"] = "strict"
        proj.write_manifest(manifest)

        readme = proj.read_layer_readme("L4-编码实现")
        proj.write_layer_readme(
            "L4-编码实现",
            {**readme, "todo_descent": 1},
            replace_todo_section(readme["content"], "## 当前待办\n\n- [x] done"),
        )

        gate = ConsistencyGate(proj)
        gate.ensure()
        # strict needs a verdict; leave it missing so the gate must reject
        (proj.root / "main.py").write_text("def main():\n    return 9\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n改\n")

        changelog = proj.vinw_dir / "changelog.md"
        before = changelog.read_text(encoding="utf-8").count("auto-audit")

        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).baseline("L4-编码实现", "strict reject")

        assert detect_drift(proj)["state"] != "clean"
        assert changelog.read_text(encoding="utf-8").count("auto-audit") == before


class TestClarificationFlow:
    """v0.17 R31: LLM-driven alignment loop (ambiguity only)."""

    def _payload(self, **over):
        base = {
            "question": "宏内核寄存器分块取 4x8 还是 6x16？",
            "layer": "L3-方案细化",
            "uncertainty": "两种分块在目标机器上性能接近，影响实现结构",
            "assumption": "按参考实现取 4x8",
            "deviation": "若你预期 6x16， packing 布局与基准口径都会不同",
            "options": json.dumps([
                {"id": "4x8", "label": "4x8", "impact": "packing 简单"},
                {"id": "6x16", "label": "6x16", "impact": "1024³ 预计 +40%"},
            ]),
        }
        base.update(over)
        return base

    def test_creates_clarification_with_auto_options(self, proj):
        import vinw.server as server

        saved = server._active_project
        server._active_project = proj
        try:
            result = json.loads(server.se_request_clarification(**self._payload()))
        finally:
            server._active_project = saved

        assert result["status"] == "pending"
        manifest = proj.read_manifest()
        cfm = next(
            c for c in manifest["pending_confirmations"]
            if c["id"] == result["confirmation_id"]
        )
        assert cfm["item_type"] == "clarification"
        ids = [o["id"] for o in cfm["options"]]
        assert "assume-ok" in ids and "other" in ids
        assert cfm["assumption"] and cfm["deviation"] and cfm["uncertainty"]

    def test_empty_uncertainty_rejected(self, proj):
        import vinw.server as server

        saved = server._active_project
        server._active_project = proj
        try:
            result = json.loads(
                server.se_request_clarification(**self._payload(uncertainty=""))
            )
        finally:
            server._active_project = saved
        assert "error" in result

    def test_reserved_option_id_rejected(self, proj):
        import vinw.server as server

        saved = server._active_project
        server._active_project = proj
        try:
            result = json.loads(
                server.se_request_clarification(**self._payload(options=json.dumps(
                    [{"id": "modify", "label": "x"}, {"id": "b", "label": "y"}]
                )))
            )
        finally:
            server._active_project = saved
        assert "error" in result

    def test_resolve_assume_ok_vs_corrected(self, proj):
        from vinw.workflow.state_machine import WorkflowEngine

        engine = WorkflowEngine(proj)
        cfm_id = engine.require_confirmation(
            item_type="clarification",
            description="q",
            options=["4x8", "6x16", "assume-ok", "other"],
            blocking=False,
            extra={
                "layer": "L3-方案细化", "question": "q", "uncertainty": "u",
                "assumption": "a", "deviation": "d", "topic_normalized": "t",
                "options": [], "recommendation": None,
            },
        )
        r1 = engine.resolve_confirmation(cfm_id, "assume-ok")
        assert r1["corrected"] is False

        cfm_id2 = engine.require_confirmation(
            item_type="clarification", description="q2",
            options=["x", "assume-ok", "other"], blocking=False,
            extra={
                "layer": "L3-方案细化", "question": "q2", "uncertainty": "u",
                "assumption": "a", "deviation": "d", "topic_normalized": "t2",
                "options": [], "recommendation": None,
            },
        )
        r2 = engine.resolve_confirmation(cfm_id2, "6x16" if False else "x")
        assert r2["corrected"] is True
        changelog = (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")
        assert "alignment" in changelog

    def test_other_requires_feedback(self, proj):
        from vinw.workflow.state_machine import WorkflowEngine
        import pytest

        engine = WorkflowEngine(proj)
        cfm_id = engine.require_confirmation(
            item_type="clarification", description="q",
            options=["a", "assume-ok", "other"], blocking=False,
            extra={
                "layer": "L1-需求拆解", "question": "q", "uncertainty": "u",
                "assumption": "a", "deviation": "d", "topic_normalized": "t",
                "options": [], "recommendation": None,
            },
        )
        with pytest.raises(ValueError):
            engine.resolve_confirmation(cfm_id, "other", "")
        ok = engine.resolve_confirmation(cfm_id, "other", "我的意思是 8x8")
        assert ok["corrected"] is True


class TestDesignHashAlgoVersioning:
    """R30-3: reports and anchors carry the algorithm tag; mismatch = stale."""

    def test_report_carries_algo(self, proj):
        import frontmatter

        store_llm(proj)
        from pathlib import Path

        reports = sorted(
            Path(proj.get_layer_dir("L4-编码实现") / "consistency-reports").glob("report-*.md"),
            key=lambda p: p.stat().st_mtime,
        )
        meta = frontmatter.load(reports[-1]).metadata
        assert meta.get("design_hash_algo") == "layer-v1"

    def test_algo_mismatch_invalidates_verdict(self, proj):
        store_llm(proj, overall="passed")
        gate = ConsistencyGate(proj)
        assert gate.llm_status()["satisfied"] is True

        # simulate an old report written before the algo tag existed
        from pathlib import Path

        reports = sorted(
            Path(proj.get_layer_dir("L4-编码实现") / "consistency-reports").glob("report-*.md"),
            key=lambda p: p.stat().st_mtime,
        )
        import re

        text = reports[-1].read_text(encoding="utf-8")
        text = re.sub(r'design_hash_algo: layer-v1\n', '', text)
        reports[-1].write_text(text, encoding="utf-8")

        assert gate.llm_status()["satisfied"] is False
        assert gate.freshness(kind="llm")["state"] == "stale_design"

    def test_server_version_in_get_project(self, proj):
        import vinw.server as server

        saved = server._active_project
        server._active_project = proj
        try:
            payload = json.loads(server.se_get_project())
        finally:
            server._active_project = saved
        assert "server_version" in payload
        assert payload["server_version"]["commit"]


class TestClarificationEdgeCases:
    """reviewer15 GAP-004: boundary coverage for v0.17."""

    def _call(self, proj, **over):
        import vinw.server as server

        base = {
            "question": "分块尺寸？", "layer": "L3-方案细化",
            "uncertainty": "两种解读", "assumption": "4x8",
            "deviation": "基准口径", "options": '["a", "b"]',
        }
        base.update(over)
        saved = server._active_project
        server._active_project = proj
        try:
            return json.loads(server.se_request_clarification(**base))
        finally:
            server._active_project = saved

    def test_string_reserved_id_rejected(self, proj):
        r = self._call(proj, options='["assume-ok", "x"]')
        assert "error" in r

    def test_mixed_array_rejected(self, proj):
        r = self._call(
            proj,
            options='["a", {"id": "b", "label": "b"}]',
        )
        assert "error" in r

    def test_empty_layer_rejected(self, proj):
        r = self._call(proj, layer="")
        assert "error" in r

    def test_recommendation_must_be_object(self, proj):
        r = self._call(proj, recommendation='"just a string"')
        assert "error" in r

    def test_recommendation_id_must_be_option(self, proj):
        r = self._call(
            proj,
            recommendation=json.dumps({"id": "nope", "reason": "x"}),
        )
        assert "error" in r

    def test_topic_default_normalizes_question(self, proj):
        import vinw.server as server

        q = "  宏内核 寄存器 分块 取 4x8 还是 6x16？"
        r = self._call(proj, question=q)
        assert r["status"] == "pending"
        manifest = server._active_project = None or proj
        cfm = next(
            c for c in proj.read_manifest()["pending_confirmations"]
            if c["id"] == r["confirmation_id"]
        )
        assert cfm["topic_normalized"] == "".join(q.split())[:32]

    def test_repeat_warning_after_two_resolved(self, proj):
        from vinw.workflow.state_machine import WorkflowEngine

        engine = WorkflowEngine(proj)

        def mk():
            return engine.require_confirmation(
                item_type="clarification", description="q",
                options=["a", "assume-ok", "other"], blocking=False,
                extra={
                    "layer": "L3-方案细化", "question": "q", "uncertainty": "u",
                    "assumption": "a", "deviation": "d",
                    "topic_normalized": "same-topic", "options": [],
                    "recommendation": None,
                },
            )

        first = mk()
        engine.resolve_confirmation(first, "assume-ok")
        second = mk()
        engine.resolve_confirmation(second, "a")
        # a purged (superseded) entry must NOT count toward the repeat warning
        third = mk()
        engine.purge_confirmations(before_descent=0, only_non_blocking=True)
        r = self._call(proj, topic="same-topic")
        assert r["status"] == "pending"
        assert "warning" in r  # two genuine resolutions -> third warns

    def test_from_finding_marks_and_rejects(self, proj):
        import vinw.server as server

        store_llm(proj, findings=[
            {"id": "AMB-1", "description": "歧义点",
             "difference": "假设A", "analysis": "可能偏离B"},
        ])
        saved = server._active_project
        server._active_project = proj
        try:
            ok = json.loads(
                server.se_request_clarification_from_finding(
                    finding_id="AMB-1", layer="L3-方案细化",
                    question="哪个？", uncertainty="低置信",
                    options='["A","B"]',
                )
            )
            assert ok["status"] == "pending"
            assert ok["finding_marked"] == "AMB-1"
            # finding 记录已带 clarification_id 标记
            from vinw.workflow.triage import AuditTriage
            import frontmatter as fm

            latest = AuditTriage(proj).latest_llm_report()
            report_path = (
                proj.get_layer_dir("L4-编码实现")
                / "consistency-reports" / f"report-{latest[0]}.md"
            )
            meta = fm.load(report_path).metadata
            marked = [f for f in meta["inconsistencies"] if f.get("id") == "AMB-1"]
            assert marked[0].get("clarification_id") == ok["confirmation_id"]

            missing = json.loads(
                server.se_request_clarification_from_finding(
                    finding_id="NOPE", layer="L3", question="?",
                    uncertainty="u", options='["a","b"]',
                )
            )
            assert "error" in missing
        finally:
            server._active_project = saved
