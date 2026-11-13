#!/usr/bin/env python3
"""Finalize L5: baseline and descend to L6."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.workflow.state_machine import WorkflowEngine
from vinw.store.changelog import append_changelog_entry

proj = Project(Path("/mnt/agents/output/vinw-design"))
engine = WorkflowEngine(proj)

# 1. Log test completion
append_changelog_entry(
    proj.vinw_dir / "changelog.md",
    change_type="test",
    layer="L5-测试验证",
    descent=1,
    scope="tests/ (36 cases)",
    reason="L5 测试验证完成：36/36 通过，5 个 bug 修复，MCP tools + TUI 验证通过",
    before="L5 待办：测试计划、单元测试、验证未执行",
    after="36 个单元测试全部通过，test-plan.md + test-results.md 已归档",
)
print("[1/4] Changelog updated")

# 2. Baseline L5
result = engine.baseline("L5-测试验证", "L5 round 1 complete: 36 tests passed, 5 bugs fixed")
print(f"[2/4] L5 baselined: {result}")

# 3. Descend to L6
result2 = engine.descend("L6-检视清理", "L5 complete, entering cleanup review")
print(f"[3/4] Descended to L6: {result2}")

# 4. Update L6 README with initial todos
l6_readme = proj.read_layer_readme("L6-检视清理")
l6_meta = {k: v for k, v in l6_readme.items() if k != "content"}
l6_content = """# L6-检视清理

## 当前待办

- [ ] 代码风格统一检查（PEP8、类型注解）
- [ ] 删除调试代码与废弃注释
- [ ] 文档完整性检查（README、docstring）
- [ ] 依赖清理（pyproject.toml 对齐）
- [ ] 最终一致性检查（method='text' 全量扫描）
- [ ] L6 基线化 → 下降到 L7

## 阶段小结

（阶段完成时填写）

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| — | — | — |
"""

proj.write_layer_readme("L6-检视清理", l6_meta, l6_content)
print("[4/4] L6 README initialized")

# Final state
manifest = proj.read_manifest()
print("\n" + "=" * 60)
print("PROJECT STATE AFTER L5 COMPLETION")
print("=" * 60)
for layer in ["L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化",
              "L4-编码实现", "L5-测试验证", "L6-检视清理", "L7-终验"]:
    s = manifest['layer_states'].get(layer, {})
    print(f"  {layer}: {s.get('status')} | baselines: {proj.list_baselines(layer)} | descents: {s.get('descent_count')}")

print(f"\nCurrent: descent-{manifest['current_descent']} @ {manifest['current_layer']}")
print("\n✅ L5 complete, L6 ready for cleanup review")
