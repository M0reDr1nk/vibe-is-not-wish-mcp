#!/usr/bin/env python3
"""Finalize L6: cleanup review, baseline, descend to L7."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.workflow.state_machine import WorkflowEngine
from vinw.store.changelog import append_changelog_entry

proj = Project(Path("/mnt/agents/output/vinw-design"))
engine = WorkflowEngine(proj)

# 1. Log cleanup completion
append_changelog_entry(
    proj.vinw_dir / "changelog.md",
    change_type="cleanup",
    layer="L6-检视清理",
    descent=1,
    scope="vinw/",
    reason="L6 检视清理完成：修复 frontmatter 缺失导入、移除废弃 consistency.py、统一 datetime.timezone、更新依赖与文档",
    before="server.py 缺少 frontmatter 导入；consistency.py 已废弃；utcnow() DeprecationWarning 残留；README 缺少新工具说明",
    after="frontmatter 导入已添加；consistency.py 已删除；所有 utcnow() 已替换；README 已更新；pyproject.toml dev 依赖已补充 scikit-learn",
)
print("[1/5] Changelog updated")

# 2. Write cleanup log
proj.write_document(
    "L6-检视清理", "cleanup-log.md",
    """---
se_version: "2.0"
layer: "L6-检视清理"
doc_type: "cleanup-log"
status: "completed"
---

# 检视清理记录

## 代码风格检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| PEP8 合规 | 通过 | 无格式问题 |
| 类型注解 | 通过 | 核心函数均有类型注解 |
| 导入清理 | 已修复 | 移除未使用的 ConsistencyChecker 导入 |

## Bug 修复

| 问题 | 严重性 | 修复 |
|------|--------|------|
| server.py 缺少 frontmatter 导入 | 🔴 高 | 已添加 `import frontmatter` |
| consistency_llm.py 残留 utcnow() | 🟡 中 | 已替换为 datetime.now(timezone.utc) |

## 废弃代码清理

| 文件 | 操作 | 原因 |
|------|------|------|
| `vinw/workflow/consistency.py` | 删除 | 已被 consistency_llm.py 替代 |

## 依赖对齐

| 变更 | 说明 |
|------|------|
| pyproject.toml dev +scikit-learn | TF-IDF 搜索需要 |

## 文档更新

| 文件 | 变更 |
|------|------|
| README.md | 添加 se_store_consistency_report、se_search_proposals 工具说明 |
| vinw/__init__.py | 添加 __version__ = "0.2.0" |

## 测试复验

- 36/36 单元测试通过 ✅
- 一致性检查：20 条 WARNING 全部为已知误报（设计项目与代码项目分离导致）
""",
    doc_type="cleanup-log"
)
print("[2/5] Cleanup log written")

# 3. Update L6 README
l6_readme = proj.read_layer_readme("L6-检视清理")
l6_meta = {k: v for k, v in l6_readme.items() if k != "content"}
l6_content = """# L6-检视清理

## 当前待办

- [x] 代码风格统一检查（PEP8、类型注解）
- [x] 删除调试代码与废弃注释（consistency.py 已移除）
- [x] 文档完整性检查（README、docstring）
- [x] 依赖清理（pyproject.toml 对齐）
- [x] 最终一致性检查（36 测试通过，一致性误报为已知限制）
- [x] L6 基线化 → 下降到 L7

## 阶段小结

descent-1 检视清理结果：

- **2 个 bug 修复**：server.py 缺少 frontmatter 导入、consistency_llm.py 残留 utcnow()
- **1 个废弃文件删除**：workflow/consistency.py
- **依赖对齐**：pyproject.toml dev 添加 scikit-learn
- **文档更新**：README 补充新工具、__init__.py 添加版本
- **测试复验**：36/36 通过

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| v001 | — | descent-1 检视清理完成 |
"""

proj.write_layer_readme("L6-检视清理", l6_meta, l6_content)
print("[3/5] L6 README updated")

# 4. Baseline L6
result = engine.baseline("L6-检视清理", "L6 round 1 complete: cleanup, bugfixes, docs updated")
print(f"[4/5] L6 baselined: {result}")

# 5. Descend to L7
result2 = engine.descend("L7-终验", "L6 complete, entering final verification")
print(f"[5/5] Descended to L7: {result2}")

# Final state
manifest = proj.read_manifest()
print("\n" + "=" * 60)
print("PROJECT STATE AFTER L6 COMPLETION")
print("=" * 60)
for layer in ["L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化",
              "L4-编码实现", "L5-测试验证", "L6-检视清理", "L7-终验"]:
    s = manifest['layer_states'].get(layer, {})
    print(f"  {layer}: {s.get('status')} | baselines: {proj.list_baselines(layer)} | descents: {s.get('descent_count')}")

print(f"\nCurrent: descent-{manifest['current_descent']} @ {manifest['current_layer']}")
print("\n✅ L6 complete, L7 ready for final verification")
