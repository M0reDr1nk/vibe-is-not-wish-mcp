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
## descent-4 新增（完成态迁移，对应 asc-003 / L3 v005）

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md v0.4 | 完成态迁移 | vinw/server.py | se_complete_project() | ✅ 已实现（前置校验+结构化 error） |
| api-design.md v0.4 | TUI completed | vinw/tui/app.py | refresh_ui 层状态图 completed 分支 | ✅ 已实现（🏁） |

## descent-5 新增（TUI 布局契约，对应 asc-004 / L3 v006）

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md v0.5 | TUI 布局契约 | vinw/tui/app.py | compose() VerticalScroll + auto Static | ✅ 已实现 |
| api-design.md v0.5 | 表格列宽约束 | vinw/tui/app.py | refresh_ui() 待办表格 | ✅ 已实现 |
| api-design.md v0.5 | 滚动验证契约 | tests/test_tui.py | test_todo_panel_is_actually_scrollable | ✅ 已实现（断言 max_scroll_y > 0） |

## descent-6 新增（待办生命周期/守卫/门控清理，对应 asc-005 / L3 v0.8）

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md v0.6 | 待办生命周期契约 | vinw/store/project.py | extract_todo_section / replace_todo_section / has_placeholder_todo | ✅ 已实现 |
| api-design.md v0.6 | 待办生命周期契约 | vinw/store/project.py | Project.rollback_to_baseline（回填现场待办） | ✅ 已实现 |
| api-design.md v0.6 | 基线占位符守卫 | vinw/workflow/state_machine.py | WorkflowEngine.baseline(force) | ✅ 已实现 |
| api-design.md v0.6 | 基线占位符守卫 | vinw/server.py | se_baseline(force) / se_complete_project 前置检查 | ✅ 已实现 |
| api-design.md v0.6 | 门控清理 | vinw/workflow/state_machine.py | WorkflowEngine.purge_confirmations | ✅ 已实现 |
| api-design.md v0.6 | 门控清理 | vinw/server.py | se_purge_confirmations | ✅ 已实现 |

## descent-7 新增（多项目跟踪管理，对应 asc-006 / L3 v0.9）

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md v0.7 | 注册表契约 | vinw/store/registry.py | ProjectRegistry（load/save/add/remove/list/prune/resolve） | ✅ 已实现 |
| api-design.md v0.7 | 注册表契约 | vinw/store/registry.py | vinw_home / is_vinw_project / normalize | ✅ 已实现 |
| api-design.md v0.7 | MCP 兼容红线 | vinw/server.py | _project_or_error（21 个工具可选 project） | ✅ 已实现 |
| api-design.md v0.7 | 新增工具 | vinw/server.py | se_register_project / se_list_projects / se_remove_project / se_prune_projects / se_use_project | ✅ 已实现 |
| api-design.md v0.7 | TUI | vinw/tui/app.py | 工作目录栏 / action_select_project / _on_project_selected | ✅ 已实现 |
| api-design.md v0.7 | TUI | vinw/tui/selector.py | ProjectSelector | ✅ 已实现 |
| api-design.md v0.7 | CLI | vinw/__main__.py | _run_project_command / _resolve_tui_target | ✅ 已实现 |

## descent-8 变更（注册表 SQLite，对应 asc-007 / L3 v0.10）

| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |
|---------|------|---------|--------|------|
| api-design.md v0.8 | SQLite schema | vinw/store/registry.py | _ensure_schema / _connect（WAL/busy_timeout） | ✅ 已实现 |
| api-design.md v0.8 | 迁移 | vinw/store/registry.py | _migrate_legacy_json / _quarantine_if_corrupt | ✅ 已实现 |
| api-design.md v0.8 | intent/observation | vinw/store/registry.py | state 列 + list(probe) 策略 + _record_probe | ✅ 已实现 |
| api-design.md v0.8 | 状态历史 | vinw/store/registry.py | _log_event / history | ✅ 已实现 |
| api-design.md v0.8 | 导出 | vinw/store/registry.py | export_json | ✅ 已实现 |
| api-design.md v0.8 | MCP | vinw/server.py | se_set_project_state / se_project_history / se_export_projects | ✅ 已实现 |
| api-design.md v0.8 | CLI | vinw/__main__.py | activate/deactivate/history/export 子命令 | ✅ 已实现 |
