"""Spiral-ascend workflow engine — baseline, ascend, descend, gate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..store.project import Project, LAYERS
from ..store.changelog import append_changelog_entry


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
            self.project.se_dir / "changelog.md",
            change_type=change_type,
            layer=layer,
            descent=descent,
            scope=scope,
            reason=reason,
            before=before,
            after=after,
        )

    # ── Baseline ──────────────────────────────────────────────

    def baseline(self, layer: str, reason: str = "") -> dict[str, Any]:
        version = self._generate_baseline_version(layer)
        self.project.freeze_baseline(layer, version, reason)

        manifest = self.project.read_manifest()
        layer_states = manifest.get("layer_states", {})
        if layer not in layer_states:
            layer_states[layer] = {}

        layer_states[layer]["status"] = "baselined"
        layer_states[layer]["latest_baseline"] = version
        layer_states[layer]["baselined_at"] = datetime.now(timezone.utc).isoformat()

        manifest["layer_states"] = layer_states
        self.project.write_manifest(manifest)

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

        # 3. Mark from_layer through L7 as superseded
        layer_states = manifest.get("layer_states", {})
        for i in range(from_idx, len(LAYERS)):
            l = LAYERS[i]
            if l in layer_states:
                layer_states[l]["status"] = "superseded"
                layer_states[l]["superseded_at"] = datetime.now(timezone.utc).isoformat()
                layer_states[l]["superseded_by"] = ascent_id

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

        # Verify intermediate layers are baselined or in_progress
        for i in range(from_idx + 1, to_idx):
            mid_layer = LAYERS[i]
            mid_state = manifest.get("layer_states", {}).get(mid_layer, {})
            if mid_state.get("status") not in ("baselined", "in_progress"):
                raise ValueError(
                    f"Intermediate layer {mid_layer} is not baselined; cannot skip to {to_layer}"
                )

        layer_states = manifest.get("layer_states", {})

        if to_layer in layer_states:
            layer_states[to_layer]["status"] = "in_progress"
            layer_states[to_layer]["descent_count"] = (
                layer_states[to_layer].get("descent_count", 0) + 1
            )
            layer_states[to_layer].pop("superseded_at", None)
            layer_states[to_layer].pop("superseded_by", None)
        else:
            layer_states[to_layer] = {"status": "in_progress", "descent_count": 1}

        manifest["current_layer"] = to_layer
        manifest["layer_states"] = layer_states
        self.project.write_manifest(manifest)

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

    # ── Layer completion ──────────────────────────────────────

    def mark_layer_completed(self, layer: str) -> None:
        """Mark a layer README as completed (pre-baseline)."""
        readme = self.project.read_layer_readme(layer)
        meta = {k: v for k, v in readme.items() if k != "content"}
        meta["status"] = "completed"
        meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.project.write_layer_readme(layer, meta, readme.get("content", ""))
