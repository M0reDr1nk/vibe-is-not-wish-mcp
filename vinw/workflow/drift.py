"""Workspace drift detection — does the code still match the audited baseline?

The project state (baseline + audit report) records a fingerprint of the code
that was verified. If the working tree changes afterwards, every "passed" mark
in the TUI becomes a lie: the project may read as completed while the code has
moved on. This module makes that divergence visible instead of silent.
"""

from __future__ import annotations

from typing import Any

from ..store.project import Project
from .consistency_gate import ConsistencyGate


def detect_drift(project: Project) -> dict[str, Any]:
    """Compare the live code/design fingerprint against the audited one.

    Returns {detected, reason, changed, baseline_fingerprint, current_fingerprint}.
    Any failure to fingerprint is reported as "unknown", never as "clean".
    """
    try:
        gate = ConsistencyGate(project)
        state = (
            project.read_manifest()
            .get("layer_states", {})
            .get("L4-编码实现", {})
            .get("consistency")
            or {}
        )
        audited = state.get("code_fingerprint")

        current = gate.current_fingerprint()
        current_fp = current["code_fingerprint"]

        if not audited:
            return {
                "detected": False,
                "reason": "no_audited_fingerprint",
                "changed": [],
                "baseline_fingerprint": None,
                "current_fingerprint": current_fp,
            }

        if audited == current_fp:
            return {
                "detected": False,
                "reason": "in_sync",
                "changed": [],
                "baseline_fingerprint": audited,
                "current_fingerprint": current_fp,
            }

        changed: list[str] = []
        report = gate.latest_llm() or gate.latest_passing(kind="llm")
        return {
            "detected": True,
            "reason": "workspace_changed_since_audit",
            "changed": changed,
            "baseline_fingerprint": audited,
            "current_fingerprint": current_fp,
            "audited_report": (report or {}).get("report_id"),
        }
    except Exception as e:  # never let drift detection break the UI
        return {
            "detected": False,
            "reason": f"unavailable: {e}",
            "changed": [],
            "baseline_fingerprint": None,
            "current_fingerprint": None,
        }


def drift_lines(project: Project) -> list[str]:
    """Human-readable drift notices for the TUI/CLI."""
    drift = detect_drift(project)
    if not drift["detected"]:
        return []
    return [
        "⚠ 工作区已偏离审计基线：当前代码与最近一次通过校验的指纹不一致",
        f"   审计指纹: {str(drift['baseline_fingerprint'])[:16]}…  "
        f"当前指纹: {str(drift['current_fingerprint'])[:16]}…",
        "   建议：重跑 se_check_consistency（text 会标记 stale_files），"
        "并按流程补齐审核后再推进",
    ]
