#!/usr/bin/env python3
"""Finalize L3 design decisions and descend to L4."""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.workflow.state_machine import WorkflowEngine
from vinw.store.changelog import append_changelog_entry

proj = Project(Path("/mnt/agents/output/vinw-design"))
engine = WorkflowEngine(proj)

# 1. Update L3 README with decision summary
l3_readme = proj.read_layer_readme("L3-方案细化")
l3_readme_meta = {k: v for k, v in l3_readme.items() if k != "content"}
l3_readme_content = l3_readme.get("content", "")

l3_readme_content += """

## 已决策遗留项

| 遗留项 | 决策 | 理由 |
|--------|------|------|
| 一致性检查深度 | **LLM 文本审计为主**，tree-sitter 强校验保留扩展能力（近期不做） | LLM 能捕捉语义级不一致；tree-sitter 作为接口签名漂移的备用防火墙，启用条件：连续 2 次以上因签名不一致触发 ascend |
| 向量检索 | **TF-IDF + ripgrep** | 当前规模下 faiss 过度设计；ripgrep 零成本，TF-IDF 在历史项目 > 50 个时无缝升级 |
"""

proj.write_layer_readme("L3-方案细化", l3_readme_meta, l3_readme_content)
print("[1/4] L3 README updated with decision summary")

# 2. Re-baseline L3 (v002)
result = engine.baseline("L3-方案细化", "遗留项决策完毕，design-doc/api-design/checkpoints 已更新")
print(f"[2/4] L3 re-baselined: {result}")

# 3. Log changes
append_changelog_entry(
    proj.vinw_dir / "changelog.md",
    change_type="design",
    layer="L3-方案细化",
    descent=1,
    scope="design-doc.md + api-design.md + checkpoints.md",
    reason="遗留项决策：一致性检查=LLM文本审计+tree-sitter预留；向量检索=TF-IDF+rg",
    before="遗留项待决策",
    after="决策完毕，L3 重新基线化 v002",
)
print("[3/4] Changelog updated")

# 4. Descend to L4
result2 = engine.descend("L4-编码实现", "设计冻结，进入编码实现阶段")
print(f"[4/4] Descended to L4: {result2}")

# 5. Update L4 README todos
l4_readme = proj.read_layer_readme("L4-编码实现")
l4_meta = {k: v for k, v in l4_readme.items() if k != "content"}
l4_content = l4_readme.get("content", "")

new_todos = """## 当前待办

- [x] 初始化 L4 工作区
- [ ] 实现 se_check_consistency (LLM 文本审计 + text fallback)
- [ ] 实现 se_search_proposals (ripgrep + TF-IDF)
- [ ] 实现代码-设计映射表维护
- [ ] 编码过程中调用 se_log_change 记录每次变更
- [ ] 编码完成后调用 se_check_consistency
"""

if re.search(r'(## 当前待办\n\n(?:- \[[ xX]\].*\n)*)', l4_content):
    l4_content = re.sub(r'(## 当前待办\n\n(?:- \[[ xX]\].*\n)*)', new_todos, l4_content)
else:
    l4_content = l4_content.rstrip() + "\n\n" + new_todos

proj.write_layer_readme("L4-编码实现", l4_meta, l4_content)

# Final state
manifest = proj.read_manifest()
print("\n" + "=" * 60)
print("FINAL STATE")
print("=" * 60)
print(f"Current: descent-{manifest['current_descent']} @ {manifest['current_layer']}")
for layer in ["L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化", "L4-编码实现"]:
    s = manifest['layer_states'].get(layer, {})
    print(f"  {layer}: {s.get('status')} | baselines: {proj.list_baselines(layer)} | descents: {s.get('descent_count')}")

print("\n✅ L3 finalized, L4 ready for implementation")
