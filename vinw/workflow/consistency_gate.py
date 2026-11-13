"""Consistency gate — fingerprint-based freshness and enforcement (L3 v0.9).

Why a gate: se_check_consistency used to be purely voluntary, and code files
are written outside MCP, so writes cannot be intercepted. Instead every layer
transition passes through a gate that compares the current code/design
fingerprint against the last passing report. That makes the check effectively
unskippable, while incremental fingerprinting avoids repeating work when
nothing changed.
"""

from __future__ import annotations

import json
from typing import Any

import frontmatter

from ..store.project import Project
from .consistency_llm import (
    LLMConsistencyAuditor,
    TextConsistencyChecker,
    aggregate_fingerprint,
    design_hash,
    layer_design_hash,
    file_hashes,
    _resolve_code_root,
)

L4 = "L4-编码实现"

FRESH = "fresh"
STALE_FILES = "stale_files"
STALE_DESIGN = "stale_design"
MISSING = "missing"


class ConsistencyGate:
    """Decide whether a consistency check is needed, and enforce it."""

    def __init__(self, project: Project):
        self.project = project
        self.reports_dir = project.get_layer_dir(L4) / "consistency-reports"

    # ── Report scanning ───────────────────────────────────────

    def _iter_reports(self):
        if not self.reports_dir.exists():
            return
        for path in sorted(self.reports_dir.glob("report-*.md")):
            try:
                post = frontmatter.load(path)
            except Exception:
                continue
            yield path, post.metadata

    def latest_passing(self, descent: int | None = None) -> dict[str, Any] | None:
        """Latest report with overall=passed, optionally restricted to a descent."""
        best: dict[str, Any] | None = None
        for path, meta in self._iter_reports():
            if meta.get("overall_status") != "passed":
                continue
            if descent is not None:
                report_descent = meta.get("descent")
                if report_descent is None or int(report_descent) != int(descent):
                    continue
            if best is None or str(meta.get("checked_at", "")) > str(
                best.get("checked_at", "")
            ):
                best = {**meta, "path": str(path)}
        return best

    # ── Freshness ─────────────────────────────────────────────

    def current_fingerprint(
        self, scope: list[str] | None = None, design_doc: str = "design-doc.md"
    ) -> dict[str, Any]:
        code_root = _resolve_code_root(self.project)
        hashes = file_hashes(code_root, scope)
        design_path = self.project.get_layer_dir("L3-方案细化") / design_doc
        # Cover the whole layer: the checks read api-design.md as well
        d_hash = layer_design_hash(self.project.get_layer_dir("L3-方案细化"))
        if not d_hash and design_path.exists():
            d_hash = design_hash(design_path)
        return {
            "file_hashes": hashes,
            "design_hash": d_hash,
            "code_fingerprint": aggregate_fingerprint(hashes, d_hash),
            "code_root": code_root,
        }

    def freshness(
        self,
        scope: list[str] | None = None,
        design_doc: str = "design-doc.md",
        descent: int | None = None,
    ) -> dict[str, Any]:
        """Classify the current state against the last passing report."""
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)

        current = self.current_fingerprint(scope, design_doc)
        report = self.latest_passing(descent)

        if report is None:
            return {"state": MISSING, "fingerprint": current, "report": None}

        stored_design = report.get("design_hash") or ""
        if stored_design and stored_design != current["design_hash"]:
            return {"state": STALE_DESIGN, "fingerprint": current, "report": report}

        stored_hashes = _parse_hashes(report.get("file_hashes"))
        if not stored_hashes:
            return {"state": MISSING, "fingerprint": current, "report": report}

        changed = sorted(
            p
            for p in set(stored_hashes) | set(current["file_hashes"])
            if stored_hashes.get(p) != current["file_hashes"].get(p)
        )
        if changed:
            return {
                "state": STALE_FILES,
                "changed": changed,
                "fingerprint": current,
                "report": report,
            }

        return {"state": FRESH, "fingerprint": current, "report": report}

    # ── Enforcement ───────────────────────────────────────────

    def ensure(
        self,
        scope: list[str] | None = None,
        design_doc: str = "design-doc.md",
        descent: int | None = None,
    ) -> dict[str, Any]:
        """Guarantee a passing report for the current code.

        fresh        -> reuse, no work
        otherwise    -> run the cheap text check, persist a report, re-judge
        """
        status = self.freshness(scope, design_doc, descent)
        if status["state"] == FRESH:
            report = status["report"] or {}
            return {
                "state": FRESH,
                "reused": True,
                "report_id": report.get("report_id"),
                "overall": report.get("overall_status"),
                "changed": [],
            }

        active_scope = scope or _scope_from_report(status.get("report"))
        checker = TextConsistencyChecker(self.project)
        result = checker.check(code_scope=active_scope)

        auditor = LLMConsistencyAuditor(self.project)
        fingerprint = status["fingerprint"]
        report_path = auditor.store_report(
            result,
            descent=descent if descent is not None else self.project.read_manifest().get("current_descent", 1),
            scope=active_scope,
            design_digest=fingerprint["design_hash"],
            hashes=fingerprint["file_hashes"],
        )

        overall = result.get("overall", "unknown")
        meta = frontmatter.load(report_path).metadata
        self._record_state(meta, overall)

        return {
            "state": status["state"],
            "reused": False,
            "report_id": meta.get("report_id"),
            "overall": overall,
            "changed": status.get("changed", []),
            "inconsistencies": len(result.get("inconsistencies", [])),
            "report_path": str(report_path),
        }

    def _record_state(self, meta: dict[str, Any], overall: str) -> None:
        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        entry = states.setdefault(L4, {})
        entry["consistency"] = {
            "report_id": meta.get("report_id"),
            "overall": overall,
            "descent": meta.get("descent"),
            "checked_at": meta.get("checked_at"),
            "code_fingerprint": meta.get("code_fingerprint"),
        }
        manifest["layer_states"] = states
        self.project.write_manifest(manifest)


def _parse_hashes(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    if isinstance(raw, str) and raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                return {str(k): str(v) for k, v in loaded.items()}
        except json.JSONDecodeError:
            return {}
    return {}


def _scope_from_report(report: dict[str, Any] | None) -> list[str] | None:
    if not report:
        return None
    scope = report.get("scope")
    if isinstance(scope, list):
        return scope
    if isinstance(scope, str) and scope.strip():
        try:
            loaded = json.loads(scope)
            return loaded if isinstance(loaded, list) else None
        except json.JSONDecodeError:
            return None
    return None
