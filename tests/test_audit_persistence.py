"""Persistence guarantees the reviewer found untested (GAP-007, INC-003, INC-013)."""

import json
import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project, replace_todo_section
from vinw.workflow.consistency_gate import ConsistencyGate
from vinw.workflow.consistency_llm import LLMConsistencyAuditor
from vinw.workflow.triage import AuditTriage


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "persist-proj"
    p = Project.init(root, "persist-proj", "")
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


def store_llm(proj, findings=None):
    gate = ConsistencyGate(proj)
    fp = gate.current_fingerprint()
    return LLMConsistencyAuditor(proj).store_report(
        {"overall": "warning", "inconsistencies": findings or [], "matched": []},
        descent=proj.read_manifest().get("current_descent", 1),
        design_digest=fp["design_hash"],
        hashes=fp["file_hashes"],
        kind="llm",
        auditor="reviewer",
    )


class TestLlmVerdictSurvivesTextRecheck:
    """INC-003: _record_state used to rebuild the dict and drop llm fields."""

    def test_llm_verdict_kept_after_code_change_and_recheck(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        path = store_llm(proj)
        import frontmatter

        gate.record_llm_state(frontmatter.load(path).metadata)
        assert proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"][
            "llm_verdict"
        ] == "warning"

        (proj.root / "main.py").write_text("def main():\n    return 3\n")
        gate.ensure()  # text re-check, non-fresh

        consistency = proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"]
        assert consistency.get("llm_verdict") == "warning", "llm state was clobbered"

    def test_tooling_discrepancy_survives_recheck(self, proj):
        gate = ConsistencyGate(proj)
        gate.ensure()
        gate.mark_discrepancy({"text_report": None, "llm_report": "x", "reason": "test"})
        assert proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"][
            "tooling_discrepancy"
        ] is True

        (proj.root / "main.py").write_text("# edit\n")
        gate.ensure()
        assert proj.read_manifest()["layer_states"]["L4-编码实现"]["consistency"].get(
            "tooling_discrepancy"
        ) is True


class TestReportIdentity:
    """INC-013: identical verdicts must not overwrite each other."""

    def test_repeated_identical_report_gets_new_id(self, proj):
        p1 = store_llm(proj, [{"id": "INC-1", "description": "x"}])
        p2 = store_llm(proj, [{"id": "INC-1", "description": "x"}])
        assert p1 != p2

    def test_triage_survives_resubmission(self, proj):
        import frontmatter

        first = store_llm(proj, [{"id": "INC-1", "description": "x"}])
        triage = AuditTriage(proj)
        triage.store({"triage": [{"id": "INC-1", "classification": "ambiguous"}]})
        assert triage.findings()[0]["status"] == "open"

        second = store_llm(proj, [{"id": "INC-1", "description": "x"}])
        assert first != second, "identical verdicts must not share a file"
        # the triaged report still carries its verdict
        meta = frontmatter.load(first).metadata
        assert meta["triage"][0]["classification"] == "ambiguous"


class TestAuditManifest:
    """INC-008: audit.auto_fixable must be a list, not a count."""

    def test_audit_lists_are_lists(self, proj):
        store_llm(proj, [{"id": "INC-1"}])
        AuditTriage(proj).store(
            {"triage": [{"id": "INC-1", "classification": "impl_bug", "confidence": "high"}]}
        )
        audit = proj.read_manifest()["layer_states"]["L4-编码实现"]["audit"]
        assert isinstance(audit["auto_fixable"], list)
        assert isinstance(audit["escalations"], list)
        assert audit["auto_fixable_count"] == len(audit["auto_fixable"])

    def test_llm_report_has_scan_metadata(self, proj):
        import frontmatter

        gate = ConsistencyGate(proj)
        gate.ensure()
        active_backup = server._active_project
        server._active_project = proj
        try:
            result = json.loads(
                server.se_store_consistency_report(
                    json.dumps({"overall": "passed", "inconsistencies": [], "matched": []}),
                    auditor="reviewer",
                )
            )
        finally:
            server._active_project = active_backup

        meta = frontmatter.load(result["report_path"]).metadata
        assert meta["kind"] == "llm"
        assert meta["files_scanned"] >= 1
        assert ".py" in meta["extensions"]
        assert meta["code_symbols_count"] >= 1


class TestStatusCannotBeSelfCertified:
    """INC-002: a caller must not be able to submit an already-decided finding."""

    def test_submitted_status_is_ignored(self, proj):
        store_llm(proj, [{"id": "INC-1"}])
        triage = AuditTriage(proj)
        triage.store(
            {
                "triage": [
                    {
                        "id": "INC-1",
                        "classification": "design_bug",
                        "confidence": "high",
                        "status": "accepted",  # attempt to self-certify
                    }
                ]
            }
        )
        assert triage.findings()[0]["status"] == "open"
        assert triage.decision()["decision"] == "escalate"


class TestUntriagedFindingsAreRoutable:
    """INC-001: untriaged findings used to raise KeyError."""

    def test_escalations_work_without_any_triage(self, proj):
        store_llm(proj, [{"id": "INC-1", "description": "x"}])
        triage = AuditTriage(proj)
        findings = triage.findings()
        assert findings[0]["status"] == "open"
        assert triage.decision()["decision"] == "escalate"
        assert triage.escalations()[0]["finding_id"] == "INC-1"

    def test_tools_do_not_crash(self, proj):
        store_llm(proj, [{"id": "INC-1", "description": "x"}])
        saved = server._active_project
        server._active_project = proj
        try:
            payload = json.loads(server.se_get_escalations())
        finally:
            server._active_project = saved
        assert payload["decision"] == "escalate"
        assert payload["count"] == 1
