"""Spiral-ascend workflow engine — baseline, ascend, descend, gate."""

from __future__ import annotations

from datetime import datetime, timezone

import frontmatter
from typing import Any

from ..store.project import (
    Project,
    LAYERS,
    TODO_PLACEHOLDER,
    has_placeholder_todo,
)
from ..store.changelog import append_changelog_entry
from .consistency_gate import ConsistencyGate
from .drift import detect_drift
from .triage import AuditTriage

L4_LAYER = 'L4-编码实现'
L5_LAYER = 'L5-测试验证'


class PlaceholderTodoError(ValueError):
    """Layer todo list is still the template placeholder."""


class ConsistencyGateError(ValueError):
    """Consistency gate did not pass for this descent."""


class LLMAuditRequiredError(ValueError):
    """Policy requires an LLM verdict that is missing."""


class ToolingDiscrepancyError(ValueError):
    """text and LLM disagree: likely an extractor defect needing triage."""


class ConsistencyConfigError(ValueError):
    """Consistency check could not run (no code files / bad config)."""


class AuditEscalationError(ValueError):
    """Audit findings need a human decision before the gate can open."""


class DesignLagError(ValueError):
    """Code moved ahead of the design: update L3 (ascend) before proceeding."""


class WorkflowEngine:
    def __init__(self, project: Project):
        self.project = project

    def _layer_index(self, layer: str) -> int:
        return LAYERS.index(layer)

    def _generate_baseline_version(self, layer: str) -> str:
        existing = self.project.list_baselines(layer)
        if not existing:
            return "v001"
        last = existing[-1]
        num = int(last.replace("v", "")) + 1
        return f"v{num:03d}"

    def _generate_ascent_id(self) -> str:
        manifest = self.project.read_manifest()
        history = manifest.get("ascent_history", [])
        return f"asc-{len(history) + 1:03d}"

    def _append_changelog(
        self,
        change_type: str,
        scope: str,
        reason: str,
        before: str = "",
        after: str = "",
    ) -> str:
        manifest = self.project.read_manifest()
        descent = manifest.get("current_descent", 1)
        layer = manifest.get("current_layer", LAYERS[0])
        return append_changelog_entry(
            self.project.vinw_dir / "changelog.md",
            change_type=change_type,
            layer=layer,
            descent=descent,
            scope=scope,
            reason=reason,
            before=before,
            after=after,
        )

    # ── State synchronisation ─────────────────────────────────

    def _sync_layer_status(
        self,
        layer: str,
        status: str,
        *,
        clear_supersede: bool = False,
        clear_redo: bool = False,
        mirror: bool = True,
    ) -> None:
        """Write a layer status to the manifest and mirror it to README.

        manifest.md is the state machine (design doc §Manifest 状态机); the
        README frontmatter is a human-facing mirror. Writing only one of them
        left the two disagreeing on nearly every layer.
        """
        if mirror:
            readme = self.project.get_layer_dir(layer) / "README.md"
            if readme.exists():
                post = frontmatter.load(readme)
                post.metadata["status"] = status
                if clear_supersede:
                    for key in ("superseded_at", "superseded_by"):
                        post.metadata.pop(key, None)
                if clear_redo:
                    post.metadata.pop("needs_redo", None)
                readme.write_text(frontmatter.dumps(post), encoding="utf-8")

    def sync_all_layer_readmes(self) -> dict[str, str]:
        """Bring every layer README status in line with the manifest."""
        manifest = self.project.read_manifest()
        states = manifest.get("layer_states", {})
        synced: dict[str, str] = {}
        for layer in LAYERS:
            status = states.get(layer, {}).get("status")
            if not status:
                continue
            self._sync_layer_status(layer, status)
            synced[layer] = status
        return synced

    # ── Layer invalidation ────────────────────────────────────

    @staticmethod
    def _invalidate_below(
        layer_states: dict[str, Any], to_idx: int, ascent_id: str
    ) -> list[str]:
        """Mark every layer below `to_idx` as needing redo. Returns the ids."""
        now = datetime.now(timezone.utc).isoformat()
        marked: list[str] = []
        for i in range(to_idx + 1, len(LAYERS)):
            layer = LAYERS[i]
            state = layer_states.get(layer)
            if not state:
                continue
            if state.get("status") in ("baselined", "completed", "in_progress"):
                state["status"] = "superseded"
                state["superseded_at"] = now
                state["superseded_by"] = ascent_id
                state["needs_redo"] = True
                marked.append(layer)
        return marked

    def repair_ascend_state(self, ascent_id: str | None = None) -> dict[str, Any]:
        """Re-apply invalidation for the latest ascent.

        Repairs state written by older builds that only superseded the layer
        the ascent started from, leaving lower layers looking completed.
        """
        manifest = self.project.read_manifest()
        history = manifest.get("ascent_history", [])
        if not history:
            return {"repaired": [], "ascent_id": None, "reason": "no ascent history"}

        record = history[-1]
        if ascent_id and record.get("id") != ascent_id:
            record = next(
                (h for h in history if h.get("id") == ascent_id), record
            )

        to_layer = record["to_layer"]
        to_idx = self._layer_index(to_layer)
        layer_states = manifest.get("layer_states", {})
        marked = self._invalidate_below(layer_states, to_idx, record["id"])

        # The current layer is where work resumes: it stays in_progress, not
        # superseded (invalidation applies to layers below it).
        current = manifest.get("current_layer")
        if current and current in layer_states and layer_states[current].get("status") == "superseded":
            layer_states[current]["status"] = "in_progress"
            layer_states[current].pop("needs_redo", None)
            if current in marked:
                marked.remove(current)

        manifest["layer_states"] = layer_states
        self.project.write_manifest(manifest)

        if marked:
            self._append_changelog(
                change_type="repair",
                scope=", ".join(marked),
                reason=(
                    f"修复 {record['id']} 的失效范围：这些层属于本轮需重做的层，"
                    f"此前误留为已完成状态"
                ),
            )
        return {"ascent_id": record["id"], "repaired": marked}

    # ── Stage-end drift healing ───────────────────────────────

    def heal_drift(self, stage: str) -> dict[str, Any] | None:
        """Re-audit when the code drifted since the last passing check.

        Called at the end of every stage transition: if the audited fingerprint
        no longer matches the working tree, the check is re-run immediately so
        a stale "passed" never survives a stage boundary. A failing re-check
        blocks the transition; a passing one is recorded as an automatic repair.
        """
        drift = detect_drift(self.project)
        state = drift.get("state")

        if state in ("clean", "unknown", None):
            # unknown means we cannot fingerprint: nothing actionable here
            return None

        # Implementation must not run ahead of the design (L3 §9): a code
        # change with no design change has to go through an ascent first.
        if state == "design_lag":
            raise DesignLagError(
                "检测到实现先于设计：代码已改动但 L3 设计未同步。"
                "请先 se_ascend 回到 L3 补设计并基线，再继续推进"
            )

        gate = ConsistencyGate(self.project)
        status = gate.ensure()
        overall = status.get("overall")

        if overall == "config_error":
            # No code to audit yet: not a drift problem, keep going. No log.
            return {"stage": stage, "drift": drift, "overall": "config_error"}

        if overall != "passed":
            raise ConsistencyGateError(
                f"{stage} 结束时检测到代码漂移，自动重审未通过"
                f"（overall={overall}，{status.get('inconsistencies', 0)} 项不一致）；"
                f"请修复后重试"
            )

        # Only a successful re-audit may leave an audit-trail entry
        self._append_changelog(
            change_type="auto-audit",
            scope=stage,
            reason=(
                f"阶段结束时检测到工作区漂移（{str(drift.get('baseline_fingerprint'))[:12]}"
                f"→{str(drift.get('current_fingerprint'))[:12]}），已自动重跑一致性检查并通过"
            ),
            before=str(drift.get("baseline_fingerprint")),
            after=str(drift.get("current_fingerprint")),
        )

        result = {"stage": stage, "healed": True, "overall": overall,
                  "report_id": status.get("report_id")}
        llm = gate.llm_status()
        if llm["required"] and not llm.get("matches_current"):
            result["needs_llm"] = True
        return result

    # ── Baseline ──────────────────────────────────────────────

    def baseline(self, layer: str, reason: str = "", force: bool = False) -> dict[str, Any]:
        # heals run after the guards below (see the call site at the end):
        # a rejected transition must not leave an auto-audit trail.
        if layer == L4_LAYER and not force:
            gate = ConsistencyGate(self.project)
            status = gate.ensure()

            if status.get("overall") == "config_error":
                raise ConsistencyConfigError(
                    f"一致性检查无法执行：{status.get('error')}"
                    f"（extensions={status.get('extensions')}, "
                    f"code_root={status.get('code_root')}）"
                )

            if status.get("overall") != "passed":
                disc = gate.discrepancy()
                if disc is not None:
                    gate.mark_discrepancy(disc)
                    raise ToolingDiscrepancyError(
                        f"text 与 LLM 结论冲突（{disc['reason']}）；"
                        f"请修提取器规则后重跑，或显式 force"
                    )
                raise ConsistencyGateError(
                    f"L4 一致性校验未通过（overall={status.get('overall')}，"
                    f"{status.get('inconsistencies', 0)} 项不一致）；"
                    f"请修复后重试，或以 force=true 跳过"
                )

            # strict: baseline also demands a semantic verdict
            if gate.policy() == "strict":
                llm = gate.llm_status()
                if not llm["satisfied"]:
                    raise LLMAuditRequiredError(
                        "策略 strict 要求基线前提供与当前代码匹配的 LLM 语义审核结论"
                    )
                triage = AuditTriage(self.project).decision()
                if triage["decision"] == "escalate":
                    raise AuditEscalationError(
                        f"{len(triage.get('escalations', []))} 条审计发现需人工裁定"
                    )
                if triage["decision"] == "auto_fix_pending":
                    raise AuditEscalationError(
                        f"{len(triage.get('auto_fixable', []))} 条高置信实现缺陷待修正"
                    )

        if not force:
            readme = self.project.read_layer_readme(layer)
            content = readme.get("content", "")
            if has_placeholder_todo(content):
                raise PlaceholderTodoError(
                    f"{layer} 待办仍为模板占位符 '{TODO_PLACEHOLDER}'；"
                    f"请先用 se_update_todo 填写真实待办，或以 force=true 跳过"
                )
        if not force:
            self.heal_drift(f"baseline:{layer}")

        version = self._generate_baseline_version(layer)
        self.project.freeze_baseline(layer, version, reason)

        manifest = self.project.read_manifest()
        layer_states = manifest.get("layer_states", {})
        if layer not in layer_states:
            layer_states[layer] = {}

        layer_states[layer]["status"] = "baselined"
        layer_states[layer]["latest_baseline"] = version
        layer_states[layer]["baselined_at"] = datetime.now(timezone.utc).isoformat()
        # A (re)baselined layer is done: stale supersede/redo markers must go
        for key in ("superseded_at", "superseded_by", "needs_redo"):
            layer_states[layer].pop(key, None)

        manifest["layer_states"] = layer_states
        self.project.write_manifest(manifest)
        self._sync_layer_status(layer, "baselined", clear_supersede=True, clear_redo=True)

        self._append_changelog(
            change_type="baseline",
            scope=f"{layer}/{version}",
            reason=reason or f"Freeze {layer} baseline {version}",
        )
        return {"layer": layer, "version": version, "status": "baselined"}

    # ── Ascend ────────────────────────────────────────────────

    def ascend(
        self,
        from_layer: str,
        to_layer: str,
        to_baseline: str,
        reason: str,
    ) -> dict[str, Any]:
        from_idx = self._layer_index(from_layer)
        to_idx = self._layer_index(to_layer)

        if to_idx >= from_idx:
            raise ValueError(
                f"Ascend only to upper layers; {to_layer} is not above {from_layer}"
            )

        if to_baseline not in self.project.list_baselines(to_layer):
            raise ValueError(f"Baseline {to_layer}/{to_baseline} does not exist")

        manifest = self.project.read_manifest()
        current_descent = manifest.get("current_descent", 1)
        ascent_id = self._generate_ascent_id()
        new_descent = current_descent + 1

        # 1. Record ascent history
        ascent_record = {
            "id": ascent_id,
            "descent_before": current_descent,
            "from_layer": from_layer,
            "to_layer": to_layer,
            "to_baseline": to_baseline,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "descent_after": new_descent,
        }

        history = manifest.get("ascent_history", [])
        history.append(ascent_record)
        manifest["ascent_history"] = history

        # 2. Rollback target layer to baseline
        self.project.rollback_to_baseline(to_layer, to_baseline)

        # 3. Everything below the ascent target must be redone in the new
        #    round — not just the layer we left.
        layer_states = manifest.get("layer_states", {})
        self._invalidate_below(layer_states, to_idx, ascent_id)

        # 4. Update target layer state
        if to_layer not in layer_states:
            layer_states[to_layer] = {}
        layer_states[to_layer]["status"] = "in_progress"
        layer_states[to_layer]["active_ascent"] = ascent_id
        layer_states[to_layer]["descent_count"] = (
            layer_states[to_layer].get("descent_count", 0) + 1
        )

        # 5. Update global state
        manifest["current_layer"] = to_layer
        manifest["current_descent"] = new_descent
        manifest["descent_started_at"] = datetime.now(timezone.utc).isoformat()
        manifest["layer_states"] = layer_states

        self.project.write_manifest(manifest)

        # Mirror to READMEs so the human-facing docs match the state machine
        self._sync_layer_status(
            to_layer, "in_progress", clear_supersede=True, clear_redo=True
        )
        for layer in LAYERS[to_idx + 1:]:
            state = layer_states.get(layer, {})
            if state.get("status") == "superseded":
                self._sync_layer_status(layer, "superseded")

        # 6. Append to ascensions.md
        self.project.append_ascent_record(ascent_record)

        # 7. Changelog
        self._append_changelog(
            change_type="ascend",
            scope=f"{from_layer}→{to_layer}({to_baseline})",
            reason=f"[{ascent_id}] {reason}",
            before=f"descent-{current_descent} @ {from_layer}",
            after=f"descent-{new_descent} @ {to_layer}",
        )

        return {
            "ascent_id": ascent_id,
            "from_layer": from_layer,
            "to_layer": to_layer,
            "new_descent": new_descent,
            "previous_descent": current_descent,
        }

    # ── Descend ───────────────────────────────────────────────

    def descend(self, to_layer: str, reason: str = "") -> dict[str, Any]:
        manifest = self.project.read_manifest()
        current_layer = manifest.get("current_layer", LAYERS[0])

        from_idx = self._layer_index(current_layer)
        to_idx = self._layer_index(to_layer)

        if to_idx <= from_idx:
            raise ValueError(
                f"Descend only to lower layers; {to_layer} is not below {current_layer}"
            )


        # Consistency must be verified before leaving L4 (covers "never ran"
        # and "code changed after the check").
        if current_layer == L4_LAYER and to_idx > from_idx:
            gate = ConsistencyGate(self.project)
            status = gate.ensure()

            if status.get("overall") == "config_error":
                raise ConsistencyConfigError(
                    f"一致性检查无法执行：{status.get('error')}"
                )
            if status.get("overall") != "passed":
                disc = gate.discrepancy()
                if disc is not None:
                    gate.mark_discrepancy(disc)
                    raise ToolingDiscrepancyError(
                        f"text 与 LLM 结论冲突（{disc['reason']}）；"
                        f"请修提取器规则后重跑，或显式 force"
                    )
                raise ConsistencyGateError(
                    f"L4 一致性校验未通过（overall={status.get('overall')}），"
                    f"不可下降到 {to_layer}"
                )

            llm = gate.llm_status()
            if llm["required"] and not llm["satisfied"]:
                if not llm["present"]:
                    detail = "尚未提供"
                elif not llm.get("matches_current"):
                    detail = "报告针对旧代码（指纹已变），需在新代码上重审"
                else:
                    detail = f"结论为 {llm.get('overall')}，未通过"
                raise LLMAuditRequiredError(
                    f"策略 {llm['policy']} 要求本轮 LLM 语义审核结论：{detail}"
                )

            disc = gate.discrepancy()
            if disc is not None:
                gate.mark_discrepancy(disc)
                raise ToolingDiscrepancyError(
                    f"text 与 LLM 结论冲突（{disc['reason']}）；"
                    f"请修提取器规则后重跑，或显式 force"
                )

            triage = AuditTriage(self.project).decision()
            if triage["decision"] == "escalate":
                raise AuditEscalationError(
                    f"{len(triage.get('escalations', []))} 条审计发现需人工裁定；"
                    f"用 se_get_escalations 查看差异点/分析/推荐，"
                    f"再以 se_record_triage_decision 裁决"
                )
            if triage["decision"] == "auto_fix_pending":
                raise AuditEscalationError(
                    f"{len(triage.get('auto_fixable', []))} 条高置信实现缺陷待修正；"
                    f"修正后调用 se_record_triage_decision(decision=fix_impl)"
                )

        # Verify intermediate layers are baselined or in_progress
        for i in range(from_idx + 1, to_idx):
            mid_layer = LAYERS[i]
            mid_state = manifest.get("layer_states", {}).get(mid_layer, {})
            if mid_state.get("status") not in ("baselined", "in_progress"):
                raise ValueError(
                    f"Intermediate layer {mid_layer} is not baselined; cannot skip to {to_layer}"
                )

        # Stage boundary: heal only once every guard above has passed
        self.heal_drift(f"descend:{current_layer}->{to_layer}")
        manifest = self.project.read_manifest()
        layer_states = manifest.get("layer_states", {})

        if to_layer in layer_states:
            layer_states[to_layer]["status"] = "in_progress"
            layer_states[to_layer]["descent_count"] = (
                layer_states[to_layer].get("descent_count", 0) + 1
            )
            layer_states[to_layer].pop("superseded_at", None)
            layer_states[to_layer].pop("superseded_by", None)
            layer_states[to_layer].pop("needs_redo", None)
        else:
            layer_states[to_layer] = {"status": "in_progress", "descent_count": 1}

        manifest["current_layer"] = to_layer
        manifest["layer_states"] = layer_states
        self.project.write_manifest(manifest)
        self._sync_layer_status(
            to_layer, "in_progress", clear_supersede=True, clear_redo=True
        )

        self._append_changelog(
            change_type="descend",
            scope=f"{current_layer}→{to_layer}",
            reason=reason or f"Descend to {to_layer}",
        )

        return {
            "from_layer": current_layer,
            "to_layer": to_layer,
            "current_descent": manifest.get("current_descent"),
        }

    # ── Gate checks ───────────────────────────────────────────

    def can_descend_to_next(self) -> tuple[bool, str, str | None]:
        manifest = self.project.read_manifest()
        current = manifest.get("current_layer", LAYERS[0])
        idx = self._layer_index(current)

        if idx >= len(LAYERS) - 1:
            return False, "Already at bottom layer L7", None

        next_layer = LAYERS[idx + 1]

        # Check blocking confirmations
        pending = manifest.get("pending_confirmations", [])
        unresolved = [
            p for p in pending if p.get("blocking", True) and not p.get("resolved_at")
        ]
        if unresolved:
            return (
                False,
                f"{len(unresolved)} unresolved blocking confirmation(s)",
                None,
            )

        # Warn if not baselined (not fatal)
        layer_state = manifest.get("layer_states", {}).get(current, {})
        if layer_state.get("status") != "baselined":
            return True, f"Warning: {current} not yet baselined; call se_baseline first", next_layer

        return True, "ok", next_layer

    # ── Confirmations ─────────────────────────────────────────

    def require_confirmation(
        self,
        item_type: str,
        description: str,
        options: list[str] | None = None,
        blocking: bool = True,
    ) -> str:
        manifest = self.project.read_manifest()
        pending = manifest.get("pending_confirmations", [])

        cfm_id = f"cfm-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{len(pending) + 1:03d}"
        cfm = {
            "id": cfm_id,
            "layer": manifest.get("current_layer"),
            "descent": manifest.get("current_descent"),
            "item_type": item_type,
            "description": description,
            "options": options or ["approve", "reject", "modify"],
            "blocking": blocking,
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
            "resolution": None,
        }
        pending.append(cfm)
        manifest["pending_confirmations"] = pending
        self.project.write_manifest(manifest)
        return cfm_id

    def resolve_confirmation(
        self, cfm_id: str, resolution: str, feedback: str = ""
    ) -> dict[str, Any]:
        manifest = self.project.read_manifest()
        pending = manifest.get("pending_confirmations", [])

        for p in pending:
            if p["id"] == cfm_id:
                p["resolved_at"] = datetime.now(timezone.utc).isoformat()
                p["resolution"] = resolution
                p["feedback"] = feedback
                break
        else:
            raise ValueError(f"Confirmation {cfm_id} not found")

        self.project.write_manifest(manifest)
        return {"id": cfm_id, "resolution": resolution}

    def purge_confirmations(
        self,
        before_descent: int = 0,
        resolution: str = "superseded",
        only_non_blocking: bool = False,
    ) -> dict[str, Any]:
        """Settle unresolved confirmations from earlier descent rounds.

        before_descent=0 settles everything older than the current descent;
        before_descent=N settles everything up to and including descent N.
        """
        manifest = self.project.read_manifest()
        pending = manifest.get("pending_confirmations", [])
        current = manifest.get("current_descent", 1)
        cutoff = before_descent if before_descent > 0 else current

        purged: list[str] = []
        now = datetime.now(timezone.utc).isoformat()
        for p in pending:
            if p.get("resolved_at"):
                continue
            descent_of_gate = p.get("descent", 0)
            if before_descent > 0:
                if descent_of_gate > before_descent:
                    continue
            elif descent_of_gate >= cutoff:
                continue
            if only_non_blocking and p.get("blocking", True):
                continue
            p["resolved_at"] = now
            p["resolution"] = resolution
            p["feedback"] = (
                f"自动结转：属于 descent-{p.get('descent')} 的过期门控，"
                f"当前已进入 descent-{current}"
            )
            purged.append(p["id"])

        if purged:
            manifest["pending_confirmations"] = pending
            self.project.write_manifest(manifest)
            self._append_changelog(
                change_type="purge-confirmations",
                scope=", ".join(purged),
                reason=f"结转 {len(purged)} 个过期门控为 {resolution}",
            )

        return {"purged": len(purged), "ids": purged, "resolution": resolution}

    # ── Layer completion ──────────────────────────────────────

    def mark_layer_completed(self, layer: str) -> None:
        """Mark a layer README as completed (pre-baseline)."""
        readme = self.project.read_layer_readme(layer)
        meta = {k: v for k, v in readme.items() if k != "content"}
        meta["status"] = "completed"
        meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.project.write_layer_readme(layer, meta, readme.get("content", ""))
