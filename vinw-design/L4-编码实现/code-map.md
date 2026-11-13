---
created_at: '2026-11-13T10:22:00.320267'
doc_type: code-map
layer: L4-编码实现
se_version: '2.0'
updated_at: '2026-11-13T10:22:00.320267'
---

# 代码-设计映射表

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