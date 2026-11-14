"""Stage boundaries must re-audit drifted work automatically (user requirement)."""

import shutil

import pytest

from vinw.store.project import Project, replace_todo_section
from vinw.workflow.consistency_gate import ConsistencyGate
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
from vinw.workflow.drift import detect_drift
from vinw.workflow.state_machine import ConsistencyGateError, WorkflowEngine


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "heal-proj"
    p = Project.init(root, "heal-proj", "")
    (root / "main.py").write_text("def main():\n    return 0\n")
    p.write_document("L3-方案细化", "api-design.md", "| 接口 |\n|------|\n| `main` |\n")
    p.write_document("L3-方案细化", "design-doc.md", "# 设计\n")
    for layer in ("L2-参考文献与方案搜证汇总", "L5-测试验证", "L6-检视清理"):
        r = p.read_layer_readme(layer)
        p.write_layer_readme(
            layer,
            {**r, "todo_descent": 1},
            replace_todo_section(r["content"], "## 当前待办\n\n- [x] done"),
        )
    yield p
    shutil.rmtree(root.parent, ignore_errors=True)


def audit(proj):
    ConsistencyGate(proj).ensure()


def changelog(proj):
    return (proj.vinw_dir / "changelog.md").read_text(encoding="utf-8")


def store_verdict(proj):
    """Store a reviewer verdict matching the current code+design."""
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


def sync_design(proj):
    """Move the design along with the code (both hashes change)."""
    proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n同步更新\n")


class TestBaselineHealsDrift:
    def test_code_only_change_is_refused(self, proj):
        """L3 §9: implementation must not run ahead of the design."""
        audit(proj)
        (proj.root / "main.py").write_text("def main():\n    return 7\n")
        assert detect_drift(proj)["state"] == "design_lag"

        from vinw.workflow.state_machine import DesignLagError

        with pytest.raises(DesignLagError):
            WorkflowEngine(proj).baseline("L2-参考文献与方案搜证汇总", "stage end")

    def test_design_and_code_change_requires_fresh_verdict(self, proj):
        """v0.15: drift healed by text is not enough; a verdict is required."""
        from vinw.workflow.state_machine import LLMAuditRequiredError

        audit(proj)
        (proj.root / "main.py").write_text("def main():\n    return 7\n")
        sync_design(proj)
        assert detect_drift(proj)["state"] == "design_synced"

        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).baseline("L2-参考文献与方案搜证汇总", "stage end")

    def test_design_and_code_change_passes_with_fresh_verdict(self, proj):
        audit(proj)
        (proj.root / "main.py").write_text("def main():\n    return 7\n")
        sync_design(proj)
        store_verdict(proj)

        WorkflowEngine(proj).baseline("L2-参考文献与方案搜证汇总", "stage end")

        assert detect_drift(proj)["state"] == "clean"
        assert "auto-audit" in changelog(proj)

    def test_baseline_blocked_when_reaudit_fails(self, proj):
        audit(proj)
        # rename the documented symbol away -> text check must fail
        (proj.root / "main.py").write_text("def renamed_away():\n    return 0\n")
        sync_design(proj)

        with pytest.raises(ConsistencyGateError):
            WorkflowEngine(proj).baseline("L2-参考文献与方案搜证汇总", "stage end")

    def test_no_audit_history_means_no_heal_needed(self, proj):
        # nothing audited yet -> no drift, no audit triggered
        result = WorkflowEngine(proj).baseline("L2-参考文献与方案搜证汇总", "first time")
        assert result["status"] == "baselined"
        assert "auto-audit" not in changelog(proj)


class TestDescendHealsDrift:
    def _at_l2(self, proj):
        manifest = proj.read_manifest()
        manifest["current_layer"] = "L2-参考文献与方案搜证汇总"
        proj.write_manifest(manifest)

    def test_descend_requires_verdict_after_drift(self, proj):
        from vinw.workflow.state_machine import LLMAuditRequiredError

        audit(proj)
        self._at_l2(proj)
        (proj.root / "main.py").write_text("def main():\n    return 42\n")
        sync_design(proj)

        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).descend("L3-方案细化", "stage end")

    def test_descend_passes_with_fresh_verdict(self, proj):
        audit(proj)
        self._at_l2(proj)
        (proj.root / "main.py").write_text("def main():\n    return 42\n")
        sync_design(proj)
        store_verdict(proj)

        WorkflowEngine(proj).descend("L3-方案细化", "stage end")

        assert detect_drift(proj)["state"] == "clean"
        assert "auto-audit" in changelog(proj)

    def test_descend_refuses_code_only_change(self, proj):
        from vinw.workflow.state_machine import DesignLagError

        audit(proj)
        self._at_l2(proj)
        (proj.root / "main.py").write_text("def main():\n    return 42\n")

        with pytest.raises(DesignLagError):
            WorkflowEngine(proj).descend("L3-方案细化", "stage end")

    def test_descend_blocked_when_reaudit_fails(self, proj):
        audit(proj)
        self._at_l2(proj)
        (proj.root / "main.py").write_text("def nope():\n    return 0\n")
        sync_design(proj)

        with pytest.raises(ConsistencyGateError):
            WorkflowEngine(proj).descend("L3-方案细化", "stage end")


class TestLlmMatching:
    def test_llm_report_tracks_fingerprint(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            policy="text+llm",
            auditor="reviewer",
        )
        assert gate.llm_status()["matches_current"] is True

        (proj.root / "main.py").write_text("def main():\n    return 1\n")
        assert gate.llm_status()["matches_current"] is False

    def test_heal_requests_llm_when_stale(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            policy="text+llm",
            auditor="reviewer",
        )
        (proj.root / "main.py").write_text("def main():\n    return 2\n")
        sync_design(proj)

        from vinw.workflow.state_machine import LLMAuditRequiredError

        with pytest.raises(LLMAuditRequiredError):
            WorkflowEngine(proj).heal_drift("baseline:test")


class TestAscendStateReset:
    """User-reported: layers below the ascent target kept showing as done."""

    def test_ascend_from_l7_resets_middle_layers(self, tmp_path):
        root = tmp_path / "reset-proj"
        proj = Project.init(root, "reset-proj", "")
        engine = WorkflowEngine(proj)

        for layer in ("L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化"):
            engine.descend(layer) if layer != "L1-需求拆解" else None
            engine.baseline(layer, "t", force=True)

        manifest = proj.read_manifest()
        manifest["current_layer"] = "L7-终验"
        manifest["layer_states"]["L4-编码实现"] = {"status": "baselined", "latest_baseline": "v001"}
        manifest["layer_states"]["L5-测试验证"] = {"status": "baselined", "latest_baseline": "v001"}
        manifest["layer_states"]["L6-检视清理"] = {"status": "baselined", "latest_baseline": "v001"}
        manifest["layer_states"]["L7-终验"] = {"status": "completed"}
        proj.write_manifest(manifest)

        engine.ascend("L7-终验", "L3-方案细化", "v001", "back to design")

        states = proj.read_manifest()["layer_states"]
        assert states["L3-方案细化"]["status"] == "in_progress"
        for layer in ("L4-编码实现", "L5-测试验证", "L6-检视清理", "L7-终验"):
            assert states[layer]["status"] == "superseded", layer
        # reference baselines survive
        assert states["L4-编码实现"]["latest_baseline"] == "v001"


class TestConfigErrorBranch:
    """GAP-006: no code to audit must not block and must not write a report."""

    def test_heal_without_code_files_is_config_error(self, tmp_path):
        root = tmp_path / "nocode"
        proj = Project.init(root, "nocode", "")
        # no code files at all, and an audited fingerprint to compare against
        manifest = proj.read_manifest()
        manifest["layer_states"] = {
            "L4-编码实现": {
                "status": "baselined",
                "consistency": {"code_fingerprint": "stale-value"},
            }
        }
        proj.write_manifest(manifest)

        reports_before = list(
            (proj.get_layer_dir("L4-编码实现") / "consistency-reports").glob("report-*.md")
        )
        result = WorkflowEngine(proj).heal_drift("baseline:test")

        assert result is not None
        assert result["overall"] == "config_error"
        reports_after = list(
            (proj.get_layer_dir("L4-编码实现") / "consistency-reports").glob("report-*.md")
        )
        assert len(reports_after) == len(reports_before), "must not persist a report"
