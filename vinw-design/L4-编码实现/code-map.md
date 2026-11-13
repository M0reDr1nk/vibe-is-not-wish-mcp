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

## descent-2 新增（自举 + 一致性定位 + .vinw 更名，对应 asc-001 / L3 v003）

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md v0.3 | 自举加载 | vinw/server.py | _try_load_bootstrap_project() | ✅ 已实现（启动自动探测 .vinw/manifest.md） |
| api-design.md v0.3 | 自举加载 | vinw/server.py | se_init_project() adopted 分支 | ✅ 已实现（接管已有工程） |
| api-design.md v0.3 | 代码定位规则 | vinw/workflow/consistency_llm.py | _resolve_code_root() | ✅ 已实现（manifest.code_root） |
| api-design.md v0.3 | 代码定位规则 | vinw/workflow/consistency_llm.py | _collect_code_files() | ✅ 已实现（文件/目录混合 + 排除目录） |
| api-design.md v0.3 | .vinw 更名 | vinw/store/project.py | Project.vinw_dir（原 se_dir） | ✅ 已重构（.se → .vinw，全仓 38 处适配） |

一致性检查报告：consistency-reports/report-c88f12f4.md（text 方法 20/20 匹配，overall: passed）

## 其他更新

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| server.py | 导入 | vinw/server.py | imports | ✅ 已更新 |