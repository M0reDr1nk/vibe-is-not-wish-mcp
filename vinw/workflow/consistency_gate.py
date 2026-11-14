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
    DESIGN_HASH_ALGO,
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

    def policy(self) -> str:
        """Audit depth policy: text | text+llm | strict."""
        return str(
            self.project.read_manifest().get("consistency_policy") or "text+llm"
        )

    def latest_passing(
        self, descent: int | None = None, kind: str | None = None
    ) -> dict[str, Any] | None:
        """Latest report with overall=passed, optionally filtered by descent/kind."""
        best: dict[str, Any] | None = None
        for path, meta in self._iter_reports():
            if meta.get("overall_status") != "passed":
                continue
            if kind is not None and (meta.get("kind") or "text") != kind:
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
        from .consistency_llm import code_extensions

        code_root = _resolve_code_root(self.project)
        # Same extension set as the text check, otherwise a file outside the
        # audited scope would still create "code changed" drift.
        hashes = file_hashes(code_root, scope, code_extensions(self.project))
        design_path = self.project.get_layer_dir("L3-方案细化") / design_doc
        # Cover the whole layer: the checks read api-design.md as well
        d_hash = layer_design_hash(self.project.get_layer_dir("L3-方案细化"))
        if not d_hash and design_path.exists():
            d_hash = design_hash(design_path)
        return {
            "file_hashes": hashes,
            "design_hash": d_hash,
            # code only: mixing the design digest in here made "code matched"
            # false whenever only the design changed
            "code_fingerprint": aggregate_fingerprint(hashes, ""),
            "code_root": code_root,
        }

    def freshness(
        self,
        scope: list[str] | None = None,
        design_doc: str = "design-doc.md",
        descent: int | None = None,
        kind: str = "text",
    ) -> dict[str, Any]:
        """Classify the current state against the last passing report."""
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)

        current = self.current_fingerprint(scope, design_doc)
        # Only a report of the same kind may justify skipping that check
        report = self.latest_passing(descent, kind=kind)

        if report is None:
            return {"state": MISSING, "fingerprint": current, "report": None}

        # v0.17: algorithm tag mismatch or missing -> stale (fail-closed,
        # intentionally tighter than the design_hash-missing handling below)
        if report.get("design_hash_algo") != DESIGN_HASH_ALGO:
            return {"state": STALE_DESIGN, "fingerprint": current, "report": report}
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

        # A configuration error must not be persisted as a consistency report.
        if result.get("error"):
            return {
                "state": status["state"],
                "error": result["error"],
                "extensions": result.get("extensions"),
                "code_root": result.get("code_root"),
                "overall": "config_error",
                "reused": False,
                "inconsistencies": 0,
            }

        auditor = LLMConsistencyAuditor(self.project)
        fingerprint = status["fingerprint"]
        report_path = auditor.store_report(
            result,
            descent=descent if descent is not None else self.project.read_manifest().get("current_descent", 1),
            scope=active_scope,
            design_digest=fingerprint["design_hash"],
            hashes=fingerprint["file_hashes"],
            kind="text",
            policy=self.policy(),
            files_scanned=result.get("files_scanned"),
            extensions=result.get("extensions"),
            code_symbols_count=result.get("code_symbols_count"),
        )

        overall = result.get("overall", "unknown")
        meta = frontmatter.load(report_path).metadata
        # Anchor only on success: a failed re-check must not refresh the
        # audited fingerprint, otherwise a retry would see a clean tree.
        if overall == "passed":
            self._record_state(meta, overall)
        else:
            # Keep the old anchor, but record which report failed so the tool
            # response can point at it without re-anchoring the baseline.
            self._record_failed_report(meta, overall)

        return {
            "state": status["state"],
            "reused": False,
            "report_id": meta.get("report_id"),
            "overall": overall,
            "changed": status.get("changed", []),
            "inconsistencies": len(result.get("inconsistencies", [])),
            "report_path": str(report_path),
        }

    def latest_llm(self, descent: int | None = None) -> dict[str, Any] | None:
        """Newest LLM report for a descent, regardless of verdict.

        A warning verdict is still a provided audit: what decides the gate is
        the triage routing, not the raw overall flag.
        """
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)
        best: dict[str, Any] | None = None
        for path, meta in self._iter_reports():
            if (meta.get("kind") or "text") != "llm":
                continue
            if meta.get("descent") is None or int(meta["descent"]) != int(descent):
                continue
            if best is None or str(meta.get("checked_at", "")) > str(
                best.get("checked_at", "")
            ):
                best = {**meta, "path": str(path)}
        return best

    def llm_matches_current(self, descent: int | None = None) -> bool:
        """Does the latest LLM report describe the current code *and* design?"""
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)
        report = self.latest_llm(descent)
        if report is None:
            return False
        current = self.current_fingerprint()
        if report.get("code_fingerprint") != current["code_fingerprint"]:
            return False
        if report.get("design_hash_algo") != DESIGN_HASH_ALGO:
            return False
        stored_design = report.get("design_hash")
        # A verdict produced against older design text is stale as well; a
        # report without a design hash cannot prove it reviewed the current
        # design, so it fails closed.
        return bool(stored_design) and stored_design == current["design_hash"]

    def llm_status(self, descent: int | None = None) -> dict[str, Any]:
        """Whether an LLM audit is required, provided, and its raw verdict."""
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)
        policy = self.policy()
        required = policy in ("text+llm", "strict")
        report = self.latest_llm(descent)
        overall = (report or {}).get("overall_status")
        return {
            "policy": policy,
            "required": required,
            "present": report is not None,
            "matches_current": self.llm_matches_current(descent),
            "overall": overall,
            # A verdict only counts for the code it was produced on; whether
            # a non-passing verdict blocks is the triage layer's decision.
            "satisfied": (not required) or self.llm_matches_current(descent),
            "report_id": (report or {}).get("report_id"),
            "auditor": (report or {}).get("auditor"),
        }

    def discrepancy(self, descent: int | None = None) -> dict[str, Any] | None:
        """text says warning while LLM says passed on the same fingerprint."""
        if descent is None:
            descent = self.project.read_manifest().get("current_descent", 1)

        text_report = None
        llm_report = self.latest_passing(descent, kind="llm")
        for path, meta in self._iter_reports():
            if (meta.get("kind") or "text") != "text":
                continue
            if meta.get("descent") is None or int(meta["descent"]) != int(descent):
                continue
            if text_report is None or str(meta.get("checked_at", "")) > str(
                text_report.get("checked_at", "")
            ):
                text_report = {**meta, "path": str(path)}

        if not text_report or not llm_report:
            return None
        if text_report.get("overall_status") != "warning":
            return None
        if text_report.get("code_fingerprint") != llm_report.get("code_fingerprint"):
            return None
        return {
            "text_report": text_report.get("report_id"),
            "llm_report": llm_report.get("report_id"),
            "reason": "text 判为不一致但 LLM 判为通过：疑似提取器缺陷（规则误报/漏提取）",
        }

    def mark_discrepancy(self, info: dict[str, Any]) -> None:
        """Persist a text/LLM conflict into the text report and manifest."""
        text_report_id = info.get("text_report")
        if text_report_id:
            path = self.reports_dir / f"report-{text_report_id}.md"
            if path.exists():
                post = frontmatter.load(path)
                post.metadata["tooling_discrepancy"] = True
                post.metadata["tooling_discrepancy_reason"] = info.get("reason")
                path.write_text(frontmatter.dumps(post), encoding="utf-8")

        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        entry = states.setdefault(L4, {})
        consistency = entry.get("consistency") or {}
        consistency["tooling_discrepancy"] = True
        consistency["tooling_discrepancy_reason"] = info.get("reason")
        entry["consistency"] = consistency
        manifest["layer_states"] = states
        self.project.write_manifest(manifest)

    def sync_audited_state(self) -> bool:
        """Re-anchor the audited fingerprint on the newest passing report.

        ensure() short-circuits when a report already matches the current
        fingerprints (fresh). In that path nothing updated the manifest, so
        drift kept reporting a stale baseline forever.
        """
        manifest = self.project.read_manifest()
        descent = manifest.get("current_descent", 1)
        current = self.current_fingerprint()["code_fingerprint"]

        if not self.latest_llm(descent) and not self.latest_passing(descent):
            return False

        report = None
        for candidate in (self.latest_llm(descent), self.latest_passing(descent)):
            if candidate and candidate.get("code_fingerprint") == current:
                report = candidate
                break
        if report is None:
            return False

        self._record_state(report, report.get("overall_status", "unknown"))
        return True

    def triage_decision(self) -> dict[str, Any]:
        """Routing decision for the latest audit findings (design v0.12)."""
        from .triage import AuditTriage  # local import avoids a cycle

        return AuditTriage(self.project).decision()

    def readiness(self, descent: int | None = None) -> dict[str, Any]:
        """Combined gate view: text ensured + llm requirement + discrepancy."""
        text_status = self.ensure()
        llm = self.llm_status(descent)
        disc = self.discrepancy(descent)
        ok = (
            text_status.get("overall") == "passed"
            and llm["satisfied"]
            and disc is None
        )
        return {
            "ok": ok,
            "text": text_status,
            "llm": llm,
            "discrepancy": disc,
        }

    def record_llm_state(self, meta: dict[str, Any]) -> None:
        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        entry = states.setdefault(L4, {})
        consistency = entry.get("consistency") or {}
        consistency.update(
            {
                "llm_report_id": meta.get("report_id"),
                "llm_verdict": meta.get("overall_status"),
                "llm_auditor": meta.get("auditor"),
                "descent": meta.get("descent"),
                # anchor the audited baseline so drift detection has a
                # reference even before the first text report exists
                "code_fingerprint": meta.get("code_fingerprint")
                or consistency.get("code_fingerprint"),
                "design_hash": meta.get("design_hash")
                or consistency.get("design_hash"),
                "design_hash_algo": DESIGN_HASH_ALGO,
                # (never overwrite an existing anchor with a missing value)
            }
        )
        entry["consistency"] = consistency
        manifest["layer_states"] = states
        self.project.write_manifest(manifest)

    def _record_failed_report(self, meta: dict[str, Any], overall: str) -> None:
        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        entry = states.setdefault(L4, {})
        consistency = entry.get("consistency") or {}
        consistency["last_failed_report"] = meta.get("report_id")
        consistency["last_failed_overall"] = overall
        consistency["last_failed_at"] = meta.get("checked_at")
        entry["consistency"] = consistency
        manifest["layer_states"] = states
        self.project.write_manifest(manifest)

    def _record_state(self, meta: dict[str, Any], overall: str) -> None:
        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        entry = states.setdefault(L4, {})
        # Merge: llm_verdict / tooling_discrepancy are written by other code
        # paths and must survive a text re-check.
        existing = entry.get("consistency") or {}
        anchor = {
            "report_id": meta.get("report_id"),
            "overall": overall,
            "descent": meta.get("descent"),
            "checked_at": meta.get("checked_at"),
            "code_fingerprint": meta.get("code_fingerprint"),
            "design_hash": meta.get("design_hash"),
            "design_hash_algo": DESIGN_HASH_ALGO,
        }
        # Never let a report missing a field erase an existing anchor value
        existing.update({k: v for k, v in anchor.items() if v is not None})
        entry["consistency"] = existing
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
