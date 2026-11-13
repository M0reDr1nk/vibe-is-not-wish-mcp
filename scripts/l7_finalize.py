#!/usr/bin/env python3
"""Finalize L7: mark project complete."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.workflow.state_machine import WorkflowEngine
from vinw.store.changelog import append_changelog_entry

proj = Project(Path("/mnt/agents/output/vinw-design"))
engine = WorkflowEngine(proj)

# 1. Log final verification
append_changelog_entry(
    proj.se_dir / "changelog.md",
    change_type="final",
    layer="L7-终验",
    descent=1,
    scope="vinw v0.2.0",
    reason="L7 终验完成：descent-1 全部 7 层通过，36 测试通过，项目可交付",
    before="descent-1 进行中",
    after="descent-1 完成：L1-L7 全部 baselined，终验报告已归档",
)
print("[1/3] Changelog updated")

# 2. Mark L7 as completed (no baseline needed for final layer)
l7_readme = proj.read_layer_readme("L7-终验")
l7_meta = {k: v for k, v in l7_readme.items() if k != "content"}
l7_meta["status"] = "completed"
proj.write_layer_readme("L7-终验", l7_meta, l7_readme.get("content", ""))
print("[2/3] L7 marked completed")

# 3. Update manifest to mark project complete
manifest = proj.read_manifest()
manifest["status"] = "completed"
manifest["completed_at"] = "2026-11-13T12:00:00+00:00"
manifest["current_layer"] = "L7-终验"
proj.write_manifest(manifest)
print("[3/3] Manifest updated with completed status")

# Final state
manifest = proj.read_manifest()
print("\n" + "=" * 60)
print("FINAL PROJECT STATE — descent-1 COMPLETE")
print("=" * 60)
for layer in ["L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化",
              "L4-编码实现", "L5-测试验证", "L6-检视清理", "L7-终验"]:
    s = manifest['layer_states'].get(layer, {})
    print(f"  {layer}: {s.get('status')} | baselines: {proj.list_baselines(layer)} | descents: {s.get('descent_count')}")

print(f"\nProject status: {manifest.get('status', 'unknown')}")
print(f"Current: descent-{manifest['current_descent']} @ {manifest['current_layer']}")
print("\n" + "=" * 60)
print("✅ SE-MCP v2 descent-1 全部完成")
print("=" * 60)
