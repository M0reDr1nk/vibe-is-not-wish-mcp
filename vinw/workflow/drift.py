"""Workspace drift detection — does the code still match the audited baseline?

The project state (baseline + audit report) records a fingerprint of the code
that was verified. If the working tree changes afterwards, every "passed" mark
in the TUI becomes a lie: the project may read as completed while the code has
moved on. This module makes that divergence visible instead of silent.
"""

from __future__ import annotations

from typing import Any

from ..store.project import Project
from .consistency_gate import ConsistencyGate, _parse_hashes


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
                "state": "unknown",
                "reason": "no_audited_fingerprint",
                "changed": [],
                "baseline_fingerprint": None,
                "current_fingerprint": current_fp,
            }

        if audited == current_fp:
            return {
                "detected": False,
                "state": "clean",
                "reason": "in_sync",
                "changed": [],
                "baseline_fingerprint": audited,
                "current_fingerprint": current_fp,
            }

        report = gate.latest_llm() or gate.latest_passing(kind="llm")
        audited_hashes = _parse_hashes((report or {}).get("file_hashes"))

        # Did the *design* move with the code? Prefer the hash recorded with the
        # audited state — the newest LLM report may belong to another descent.
        audited_design = state.get("design_hash") or (report or {}).get("design_hash")
        design_changed = bool(
            audited_design and audited_design != current["design_hash"]
        )
        current_hashes = current["file_hashes"]
        if audited_hashes:
            changed = sorted(
                f"{'added' if p not in audited_hashes else 'removed' if p not in current_hashes else 'modified'}:{p}"
                for p in set(audited_hashes) | set(current_hashes)
                if audited_hashes.get(p) != current_hashes.get(p)
            )
        else:
            changed = []
        # Without a recorded design hash we cannot claim the design lagged;
        # say "drifted" and let the next audit establish the baseline.
        if not audited_design:
            state = "drifted"
            reason = "code_changed_since_audit_design_unknown"
        elif design_changed:
            state = "design_synced"
            reason = "code_and_design_changed_since_audit"
        else:
            state = "design_lag"
            reason = "code_changed_without_design_update"
        return {
            "detected": True,
            "state": state,
            "design_changed": design_changed,
            "reason": reason,
            "changed": changed,
            "baseline_fingerprint": audited,
            "current_fingerprint": current_fp,
            "audited_report": (report or {}).get("report_id"),
        }
    except Exception as e:  # never let drift detection break the UI
        return {
            "detected": False,
            "state": "unknown",
            "reason": f"unavailable: {e}",
            "changed": [],
            "baseline_fingerprint": None,
            "current_fingerprint": None,
        }


def drift_lines(project: Project) -> list[str]:
    """Human-readable drift notices for the TUI/CLI (clean yields nothing)."""
    drift = detect_drift(project)
    if drift.get("state") == "unknown":
        return [
            f"⚠ 无法判定工作区是否漂移（{drift.get('reason')}）；"
            "指纹不可用不代表与基线一致",
        ]
    if not drift.get("detected"):
        return []

    lines = [
        "⚠ 工作区已偏离审计基线：当前代码与最近一次通过校验的指纹不一致",
        f"   审计指纹: {str(drift['baseline_fingerprint'])[:16]}…  "
        f"当前指纹: {str(drift['current_fingerprint'])[:16]}…",
    ]
    changed = drift.get("changed") or []
    if changed:
        lines.append(f"   变更文件（{len(changed)}）: " + ", ".join(changed[:5]))
        if len(changed) > 5:
            lines.append(f"   … 另有 {len(changed) - 5} 个文件")
    if drift.get("state") == "design_lag":
        lines.insert(
            0,
            "🚫 实现跑在设计前面：代码已改动，但 L3 设计文档未同步更新",
        )
        lines.append(
            "   处置：先把变更补进 L3 设计（走 ascend 改设计），再重新审计；"
            "不接受「只改代码不改设计」"
        )
    else:
        lines.append(
            "   建议：重跑 se_check_consistency（text 会标记 stale_files），"
            "并按流程补齐审核后再推进"
        )
    return lines
