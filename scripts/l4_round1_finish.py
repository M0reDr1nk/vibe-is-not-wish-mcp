#!/usr/bin/env python3
"""L4 round 1: update code-map, changelog, and todos."""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.store.changelog import append_changelog_entry

proj = Project(Path("/mnt/agents/output/vinw-design"))

# 1. Update code-map.md
proj.write_document(
    "L4-编码实现", "code-map.md",
    """# 代码-设计映射表

## se_check_consistency (LLM 文本审计 + text fallback)

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md | 一致性检查 | vinw/workflow/consistency_llm.py | LLMConsistencyAuditor.audit() | ✅ 已实现 |
| api-design.md | 一致性检查 | vinw/workflow/consistency_llm.py | LLMConsistencyAuditor.store_report() | ✅ 已实现 |
| api-design.md | 一致性检查 | vinw/workflow/consistency_llm.py | TextConsistencyChecker.check() | ✅ 已实现 |
| api-design.md | 一致性检查 | vinw/server.py | se_check_consistency() | ✅ 已更新(method参数) |
| api-design.md | 一致性检查 | vinw/server.py | se_store_consistency_report() | ✅ 已新增 |

## se_search_proposals (ripgrep + TF-IDF)

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md | 方案检索 | vinw/workflow/search.py | ProposalSearcher.search() | ✅ 已实现 |
| api-design.md | 方案检索 | vinw/workflow/search.py | ProposalSearcher._search_rg() | ✅ 已实现 |
| api-design.md | 方案检索 | vinw/workflow/search.py | ProposalSearcher._search_tfidf() | ✅ 已实现 |
| api-design.md | 方案检索 | vinw/server.py | se_search_proposals() | ✅ 已新增 |

## 其他更新

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| server.py | 导入 | vinw/server.py | imports | ✅ 已更新 |
""",
    doc_type="code-map"
)
print("[1/4] code-map.md updated")

# 2. Log changes
append_changelog_entry(
    proj.vinw_dir / "changelog.md",
    change_type="code",
    layer="L4-编码实现",
    descent=1,
    scope="vinw/workflow/consistency_llm.py + search.py + server.py",
    reason="实现 se_check_consistency (LLM审计+text fallback) 和 se_search_proposals (rg+TF-IDF)",
    before="L4 待办：一致性检查和方案搜索未实现",
    after="LLMConsistencyAuditor + TextConsistencyChecker + ProposalSearcher 已实现并注册为 MCP tools",
)
print("[2/4] Changelog updated")

# 3. Update L4 README todos
l4_readme = proj.read_layer_readme("L4-编码实现")
l4_meta = {k: v for k, v in l4_readme.items() if k != "content"}
l4_content = l4_readme.get("content", "")

new_todos = """## 当前待办

- [x] 初始化 L4 工作区
- [x] 实现 se_check_consistency (LLM 文本审计 + text fallback)
- [x] 实现 se_search_proposals (ripgrep + TF-IDF)
- [x] 实现代码-设计映射表维护
- [x] 编码过程中调用 se_log_change 记录每次变更
- [ ] 编码完成后调用 se_check_consistency (使用 method='text' 做第一轮验证)
- [ ] L4 基线化 → 下降到 L5
"""

if re.search(r'(## 当前待办\n\n(?:- \[[ xX]\].*\n)*)', l4_content):
    l4_content = re.sub(r'(## 当前待办\n\n(?:- \[[ xX]\].*\n)*)', new_todos, l4_content)
else:
    l4_content = l4_content.rstrip() + "\n\n" + new_todos

proj.write_layer_readme("L4-编码实现", l4_meta, l4_content)
print("[3/4] L4 README todos updated")

# 4. Verify new files exist
mcp_root = Path("/mnt/agents/output/vinw-code")
files = [
    "vinw/workflow/consistency_llm.py",
    "vinw/workflow/search.py",
]
print("\n[4/4] File verification:")
for f in files:
    p = mcp_root / f
    print(f"  {'✅' if p.exists() else '❌'} {f} ({p.stat().st_size} bytes)")

# Show tools
from vinw.server import mcp
import asyncio
async def list_tools():
    tools = await mcp.list_tools()
    return [t.name for t in tools]
tool_names = asyncio.get_event_loop().run_until_complete(list_tools())
new_tools = [t for t in tool_names if t in ['se_check_consistency', 'se_store_consistency_report', 'se_search_proposals']]
print(f"\nNew MCP tools: {new_tools}")

# Final state
manifest = proj.read_manifest()
print("\n" + "=" * 60)
print("L4 IMPLEMENTATION STATE")
print("=" * 60)
print(f"Current: descent-{manifest['current_descent']} @ {manifest['current_layer']}")
l4_state = manifest['layer_states'].get('L4-编码实现', {})
print(f"L4 status: {l4_state.get('status')}, descents: {l4_state.get('descent_count')}")
print("\n✅ L4 round 1 complete")
