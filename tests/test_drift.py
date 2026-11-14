"""Tests for workspace drift detection."""

import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project
from vinw.workflow.consistency_gate import ConsistencyGate
from vinw.workflow.drift import detect_drift, drift_lines


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "drift-proj"
    p = Project.init(root, "drift-proj", "")
    (root / "main.py").write_text("def main():\n    return 0\n")
    p.write_document("L3-方案细化", "api-design.md", "| 接口 |\n|------|\n| `main` |\n")
    p.write_document("L3-方案细化", "design-doc.md", "# 设计\n")
    yield p
    shutil.rmtree(root.parent, ignore_errors=True)


class TestDriftDetection:
    def test_no_audit_means_unknown_not_clean(self, proj):
        result = detect_drift(proj)
        assert result["detected"] is False
        assert result["reason"] == "no_audited_fingerprint"

    def test_in_sync_after_check(self, proj):
        ConsistencyGate(proj).ensure()
        result = detect_drift(proj)
        assert result["detected"] is False
        assert result["reason"] == "in_sync"

    def test_detected_after_code_change(self, proj):
        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("def main():\n    return 1\n")
        result = detect_drift(proj)
        assert result["detected"] is True
        assert result["baseline_fingerprint"] != result["current_fingerprint"]
        # a code-only change is design lag (see TestDesignLag)
        assert result["reason"] in (
            "workspace_changed_since_audit",
            "code_changed_without_design_update",
        )

    def test_detected_after_design_change(self, proj):
        ConsistencyGate(proj).ensure()
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n变更\n")
        assert detect_drift(proj)["detected"] is True

    def test_drift_lines_explain(self, proj):
        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("# changed\n")
        lines = drift_lines(proj)
        assert any("偏离审计基线" in line for line in lines)
        # code-only change is reported as design lag, with its own guidance
        assert any("实现跑在设计前面" in line or "se_check_consistency" in line
                   for line in lines)

    def test_no_lines_when_clean(self, proj):
        ConsistencyGate(proj).ensure()
        assert drift_lines(proj) == []

    def test_unavailable_is_not_reported_as_clean(self, proj, monkeypatch):
        def boom(self):
            raise RuntimeError("fingerprint unavailable")

        monkeypatch.setattr(ConsistencyGate, "current_fingerprint", boom)
        result = detect_drift(proj)
        assert result["detected"] is False
        assert result["reason"].startswith("unavailable")


class TestApiExposure:
    def test_get_project_reports_drift(self, proj):
        import json

        ConsistencyGate(proj).ensure()
        server._active_project = proj
        try:
            payload = json.loads(server.se_get_project())
        finally:
            server._active_project = None
        assert payload["drift"]["detected"] is False

        (proj.root / "main.py").write_text("# edit\n")
        server._active_project = proj
        try:
            payload = json.loads(server.se_get_project())
        finally:
            server._active_project = None
        assert payload["drift"]["detected"] is True


class TestDriftDetails:
    """Reviewer findings INC-010 / INC-011."""

    def test_changed_lists_modified_files(self, proj):
        import frontmatter

        from vinw.workflow.consistency_llm import LLMConsistencyAuditor

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
        (proj.root / "main.py").write_text("def main():\n    return 5\n")

        result = detect_drift(proj)
        assert result["changed"], "changed must not be empty when drift is detected"
        assert any("main.py" in entry for entry in result["changed"])

    def test_unknown_state_is_not_clean(self, proj, monkeypatch):
        def boom(self):
            raise RuntimeError("cannot fingerprint")

        monkeypatch.setattr(ConsistencyGate, "current_fingerprint", boom)
        result = detect_drift(proj)
        assert result["state"] == "unknown"
        assert drift_lines(proj), "unknown must surface a warning, not silence"

    def test_clean_state_has_no_lines(self, proj):
        ConsistencyGate(proj).ensure()
        assert detect_drift(proj)["state"] == "clean"
        assert drift_lines(proj) == []


class TestDesignLag:
    """A code change without a design change means implementation ran ahead."""

    def _audit_with_design(self, proj):
        import frontmatter

        from vinw.workflow.consistency_llm import LLMConsistencyAuditor

        gate = ConsistencyGate(proj)
        gate.ensure()
        fp = gate.current_fingerprint()
        return LLMConsistencyAuditor(proj).store_report(
            {"overall": "passed", "inconsistencies": [], "matched": []},
            descent=proj.read_manifest().get("current_descent", 1),
            design_digest=fp["design_hash"],
            hashes=fp["file_hashes"],
            kind="llm",
            auditor="reviewer",
        )

    def test_code_only_change_is_design_lag(self, proj):
        self._audit_with_design(proj)
        (proj.root / "main.py").write_text("def main():\n    return 11\n")

        result = detect_drift(proj)
        assert result["state"] == "design_lag"
        assert result["design_changed"] is False
        assert result["reason"] == "code_changed_without_design_update"
        assert any("实现跑在设计前面" in line for line in drift_lines(proj))

    def test_code_and_design_change_is_design_synced(self, proj):
        self._audit_with_design(proj)
        (proj.root / "main.py").write_text("def main():\n    return 12\n")
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n同步更新\n")

        result = detect_drift(proj)
        assert result["state"] == "design_synced"
        assert result["design_changed"] is True
        assert result["reason"] == "code_and_design_changed_since_audit"
        assert not any("实现跑在设计前面" in line for line in drift_lines(proj))
