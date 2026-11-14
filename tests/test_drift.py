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
        assert "workspace_changed_since_audit" == result["reason"]

    def test_detected_after_design_change(self, proj):
        ConsistencyGate(proj).ensure()
        proj.write_document("L3-方案细化", "design-doc.md", "# 设计\n\n变更\n")
        assert detect_drift(proj)["detected"] is True

    def test_drift_lines_explain(self, proj):
        ConsistencyGate(proj).ensure()
        (proj.root / "main.py").write_text("# changed\n")
        lines = drift_lines(proj)
        assert any("偏离审计基线" in line for line in lines)
        assert any("se_check_consistency" in line for line in lines)

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
