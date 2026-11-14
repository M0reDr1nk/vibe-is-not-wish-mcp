"""Audit finding triage — classify findings and route them (L3 v0.12).

An inconsistency is not automatically an implementation bug. Findings carry a
classification and a confidence, and only `impl_bug` + `high` may be fixed
automatically; everything else has to reach a human with a structured
escalation (difference / analysis / recommendation / impact).
"""

from __future__ import annotations

import json
from typing import Any

import frontmatter

from ..store.project import Project
from .consistency_gate import L4

CLASSIFICATIONS = ("impl_bug", "design_bug", "design_gap", "ambiguous")
CONFIDENCES = ("high", "medium", "low")
DECISIONS = ("fix_impl", "fix_design", "accept_as_is", "defer")

# decision -> resulting status
DECISION_STATUS = {
    "fix_impl": "fixed",
    "fix_design": "decided",
    "accept_as_is": "accepted",
    "defer": "open",
}


class TriageError(ValueError):
    """Invalid triage payload."""


def normalize_finding(raw: dict[str, Any]) -> dict[str, Any]:
    raw_class = raw.get("classification")
    raw_conf = raw.get("confidence")
    classification = str(raw_class or "untriaged")
    confidence = str(raw_conf or "untriaged")
    if classification not in CLASSIFICATIONS:
        classification = "ambiguous"
    if confidence not in CONFIDENCES:
        confidence = "low"
    finding_id = raw.get("id") or raw.get("finding_id") or "FINDING"
    return {
        "id": finding_id,
        "finding_id": finding_id,
        "kind": raw.get("kind") or ("gap" if raw.get("missing") else "inconsistency"),
        "classification": classification,
        "confidence": confidence,
        "recommendation": raw.get("recommendation") or "",
        "difference": raw.get("difference")
        or _difference_from(raw),
        "analysis": raw.get("analysis") or raw.get("description") or "",
        "impact": raw.get("impact") or "",
        "design_ref": raw.get("design_ref"),
        "code_ref": raw.get("code_ref"),
        "severity": raw.get("severity") or "warning",
        "status": raw.get("status") or "open",
    }


def _difference_from(raw: dict[str, Any]) -> str:
    design = raw.get("design_ref") or "设计未指明"
    code = raw.get("code_ref") or "无对应实现"
    desc = raw.get("description") or raw.get("missing") or ""
    return f"设计侧: {design} | 代码侧: {code} | {desc}"


def _untriaged(raw: dict[str, Any], kind: str, fallback_id: str) -> dict[str, Any]:
    """A report finding with no verdict yet: always routable, never crashy."""
    finding = {
        "id": raw.get("id") or fallback_id,
        "kind": kind,
        "classification": raw.get("classification") or "untriaged",
        "confidence": raw.get("confidence") or "untriaged",
        "description": raw.get("description"),
        "design_ref": raw.get("design_ref"),
        "code_ref": raw.get("code_ref"),
        "severity": raw.get("severity"),
        "difference": raw.get("difference")
        or _difference_from({**raw, "design_ref": raw.get("design_ref")}),
        "analysis": raw.get("analysis") or raw.get("description") or "",
        "recommendation": raw.get("recommendation") or "",
        "impact": raw.get("impact") or "",
        # A report finding that was never triaged is open by definition
        "status": raw.get("status") or "open",
    }
    finding["finding_id"] = finding["id"]
    return finding


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]


def is_untriaged(finding: dict[str, Any]) -> bool:
    """No verdict yet: classification/confidence missing or the sentinel."""
    cls = finding.get("classification")
    conf = finding.get("confidence")
    return (
        not cls
        or not conf
        or cls == "untriaged"
        or conf == "untriaged"
    )


def requires_human(finding: dict[str, Any]) -> bool:
    """Anything not a high-confidence implementation bug needs a human."""
    if not finding.get("classification") or not finding.get("confidence"):
        return True  # untriaged findings always need routing
    return not (
        finding["classification"] == "impl_bug"
        and finding["confidence"] == "high"
    )


class AuditTriage:
    """Read/write triage verdicts and decide whether a gate may open."""

    def __init__(self, project: Project):
        self.project = project

    # ── Storage ───────────────────────────────────────────────

    def _report_path(self, report_id: str):
        return (
            self.project.get_layer_dir(L4)
            / "consistency-reports"
            / f"report-{report_id}.md"
        )

    def latest_llm_report(
        self, descent: int | None = None
    ) -> tuple[str, dict[str, Any]] | None:
        """Newest kind=llm report for a descent (defaults to the current one)."""
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)
        reports_dir = self.project.get_layer_dir(L4) / "consistency-reports"
        best: tuple[str, dict[str, Any]] | None = None
        if not reports_dir.exists():
            return None
        for path in sorted(reports_dir.glob("report-*.md")):
            try:
                meta = dict(frontmatter.load(path).metadata)
            except Exception:
                continue
            if (meta.get("kind") or "text") != "llm":
                continue
            if meta.get("descent") is None or int(meta["descent"]) != int(descent):
                continue
            if best is None or str(meta.get("checked_at", "")) > str(
                best[1].get("checked_at", "")
            ):
                best = (str(meta.get("report_id") or path.stem.replace("report-", "")), meta)
        return best

    def findings(self) -> list[dict[str, Any]]:
        """Triage verdicts; falls back to untriaged report findings."""
        latest = self.latest_llm_report()
        if latest is None:
            return []
        _, meta = latest

        raw = meta.get("triage")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = []

        if raw:
            return [normalize_finding(r) for r in raw]

        # No verdicts yet: expose the raw findings so triage can be performed
        candidates: list[dict[str, Any]] = []
        for inc in _as_list(meta.get("inconsistencies")):
            candidates.append(
                _untriaged(
                    inc,
                    kind="inconsistency",
                    fallback_id=f"INC-{len(candidates) + 1:03d}",
                )
            )
        for gap in _as_list(meta.get("gaps")):
            candidates.append(
                _untriaged(
                    gap, kind="gap", fallback_id=f"GAP-{len(candidates) + 1:03d}"
                )
            )
        return candidates

    def store(self, report_json: dict[str, Any], report_id: str | None = None) -> dict[str, Any]:
        """Attach triage verdicts to the latest LLM report (or a given one)."""
        if report_id is None:
            latest = self.latest_llm_report()
            if latest is None:
                raise TriageError("没有可附着的 LLM 报告：先提交 se_store_consistency_report")
            report_id = latest[0]

        path = self._report_path(report_id)
        if not path.exists():
            raise TriageError(f"报告不存在: {report_id}")

        items = report_json.get("triage") or report_json.get("findings") or []
        if not isinstance(items, list):
            raise TriageError("triage 必须是数组")

        # Partial triage silently drops the rest, which is worse than a forged
        # status: every finding in the report must be adjudicated.
        report_meta = frontmatter.load(path).metadata
        expected = {
            str(f.get("id"))
            for f in (
                _as_list(report_meta.get("inconsistencies"))
                + _as_list(report_meta.get("gaps"))
            )
            if f.get("id")
        }
        provided = {str(item.get("id")) for item in items if item.get("id")}
        missing = sorted(expected - provided)
        if missing:
            raise TriageError(
                f"triage 未覆盖报告全部发现，缺少: {', '.join(missing)}"
                f"（覆盖性约束：部分裁定会静默丢弃未处理项）"
            )

        findings = []
        for item in items:
            finding = normalize_finding(item)
            # status is system-maintained: a caller cannot self-certify
            finding["status"] = "open"
            finding.pop("decision", None)
            finding.pop("decision_note", None)
            findings.append(finding)
        post = frontmatter.load(path)
        post.metadata["triage"] = findings
        post.metadata["triage_counts"] = self._counts(findings)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

        self._write_audit_state(report_id)
        return {"report_id": report_id, "findings": len(findings), **self._counts(findings)}

    # ── Decisions ─────────────────────────────────────────────

    def record_decision(
        self, finding_id: str, decision: str, note: str = ""
    ) -> dict[str, Any]:
        if decision not in DECISIONS:
            raise TriageError(f"decision 必须是 {DECISIONS}")
        latest = self.latest_llm_report()
        if latest is None:
            raise TriageError("没有 LLM 报告可裁定")
        report_id, _ = latest

        path = self._report_path(report_id)
        post = frontmatter.load(path)
        findings = post.metadata.get("triage") or []
        if isinstance(findings, str):
            findings = json.loads(findings)

        hit = None
        for item in findings:
            if item.get("id") == finding_id:
                item["status"] = DECISION_STATUS[decision]
                item["decision"] = decision
                item["decision_note"] = note
                hit = item
                break
        if hit is None:
            raise TriageError(f"未找到 finding: {finding_id}")

        post.metadata["triage"] = findings
        post.metadata["triage_counts"] = self._counts(findings)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        self._write_audit_state(report_id)
        return {"finding_id": finding_id, "decision": decision, "status": hit["status"]}

    # ── Gate decision ─────────────────────────────────────────

    def decision(self) -> dict[str, Any]:
        latest = self.latest_llm_report()
        if latest is None:
            return {"decision": "no_llm_report", "findings": 0}
        report_id, _ = latest
        findings = self.findings()
        if not findings:
            return {"decision": "clear", "report_id": report_id, "findings": 0}

        open_findings = [f for f in findings if f.get("status") == "open"]
        untriaged = [f for f in findings if is_untriaged(f)]
        auto_open = [
            f for f in open_findings if not is_untriaged(f) and not requires_human(f)
        ]
        human_open = [
            f for f in open_findings if not is_untriaged(f) and requires_human(f)
        ]

        # Untriaged findings cannot be routed: they must reach a human
        if untriaged:
            return {
                "decision": "escalate",
                "report_id": report_id,
                "findings": len(findings),
                "untriaged": [f["id"] for f in untriaged],
                "escalations": untriaged,
            }
        if human_open:
            return {
                "decision": "escalate",
                "report_id": report_id,
                "findings": len(findings),
                "escalations": human_open,
            }
        if auto_open:
            return {
                "decision": "auto_fix_pending",
                "report_id": report_id,
                "findings": len(findings),
                "auto_fixable": auto_open,
            }
        # Everything decided. Distinguish "we fixed/blessed everything" from
        # "the remainder needs design work" (they used to collapse into
        # auto_fixable, which reads as the opposite of what it meant).
        needs_design = [
            f for f in findings if f["classification"] in ("design_bug", "design_gap")
        ]
        if needs_design:
            return {
                "decision": "resolved",
                "report_id": report_id,
                "findings": len(findings),
                "design_followups": [f["id"] for f in needs_design],
                "decided": len(findings),
            }
        return {
            "decision": "auto_fixable",
            "report_id": report_id,
            "findings": len(findings),
            "decided": len([f for f in findings if f["status"] != "open"]),
        }

    def escalations(self) -> list[dict[str, Any]]:
        return [
            f
            for f in self.findings()
            if requires_human(f) and f.get("status") == "open"
        ]

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _counts(findings: list[dict[str, Any]]) -> dict[str, Any]:
        by_class: dict[str, int] = {}
        for f in findings:
            by_class[f["classification"]] = by_class.get(f["classification"], 0) + 1
        return {
            "total": len(findings),
            "open": len([f for f in findings if f["status"] == "open"]),
            "by_classification": by_class,
        }

    def _write_audit_state(self, report_id: str) -> None:
        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        entry = states.setdefault(L4, {})
        decision = self.decision()
        escalation_ids = [f["id"] for f in decision.get("escalations", []) or []]
        auto_ids = [f["id"] for f in decision.get("auto_fixable", []) or []]
        entry["audit"] = {
            "report_id": report_id,
            "decision": decision.get("decision"),
            "findings": decision.get("findings", 0),
            "escalations": escalation_ids,
            "escalations_count": len(escalation_ids),
            "auto_fixable": auto_ids,
            "auto_fixable_count": len(auto_ids),
        }
        manifest["layer_states"] = states
        self.project.write_manifest(manifest)
