---
se_version: "2.0"
layer: "L5-测试验证"
doc_type: "test-results"
status: "completed"
updated_at: "2026-11-13T12:00:00Z"
---

# 测试结果

## 执行摘要

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-1 round 1 |
| 总用例数 | 36 |
| 通过 | 36 |
| 失败 | 0 |
| 错误 | 0 |
| 覆盖率 | 核心路径全覆盖 |

## 详细结果

### 1. 存储层 (test_project.py) — 10/10 ✅

| 用例 | 结果 | 说明 |
|------|------|------|
| test_directory_structure | PASS | 目录树、manifest、changelog、ascensions 正确创建 |
| test_all_layers_created | PASS | 7 层目录 + README + .baseline 全部存在 |
| test_manifest_initial_state | PASS | name/current_layer/current_descent 正确 |
| test_freeze_baseline | PASS | 基线冻结成功，版本递增 |
| test_rollback_to_baseline | PASS | 回滚成功，标记 rolled_back_from |
| test_baseline_versions_increment | PASS | v001 → v002 正确 |
| test_write_and_read | PASS | 文档 CRUD 正常 |
| test_read_nonexistent | PASS | 异常正确抛出 FileNotFoundError |
| test_get_todos | PASS | todo 扫描正确（含跨层） |
| test_changelog_append | PASS | 变更日志原子追加正常 |

### 2. 工作流引擎 (test_state_machine.py) — 13/13 ✅

| 用例 | 结果 | 说明 |
|------|------|------|
| test_baseline_updates_state | PASS | manifest 状态更新为 baselined |
| test_descend_to_next_layer | PASS | 下降后 current_layer 更新 |
| test_descend_skip_unbaselined_fails | PASS | 跳过未基线层正确拒绝 |
| test_descend_upward_fails | PASS | 反向下降正确拒绝 |
| test_ascent_creates_new_descent | PASS | descent_count 递增 |
| test_ascent_marks_lower_superseded | PASS | from_layer 及以下标记 superseded |
| test_ascent_to_same_or_lower_fails | PASS | 无效上升正确拒绝 |
| test_ascent_nonexistent_baseline_fails | PASS | 不存在的基线正确拒绝 |
| test_require_confirmation | PASS | 确认项生成正确，含 blocking 标记 |
| test_resolve_confirmation | PASS | 确认解析正确 |
| test_can_descend_with_pending_blocks | PASS | 未解析阻塞项阻止下降 |

### 3. 一致性检查 (test_consistency_llm.py) — 8/8 ✅

| 用例 | 结果 | 说明 |
|------|------|------|
| test_no_symbols_returns_passed | PASS | 空符号时返回 passed |
| test_symbol_extraction | PASS | 从 markdown 正确提取 se_* 工具名 |
| test_symbol_match_found | PASS | 代码中存在设计符号时标记 matched |
| test_symbol_missing_reported | PASS | 代码中不存在时标记 inconsistency |
| test_header_not_extracted | PASS | 表格表头（如 layer）不再被误提取 |
| test_audit_prepares_prompt | PASS | LLM prompt 构造成功（含安全替换） |
| test_audit_missing_design_error | PASS | 缺少设计文档时返回 error |
| test_store_report | PASS | 报告写入 consistency-reports/ 成功 |

### 4. 方案搜索 (test_search.py) — 7/7 ✅

| 用例 | 结果 | 说明 |
|------|------|------|
| test_rg_finds_matching_docs | PASS | ripgrep 方法命中正确文档 |
| test_rg_no_results | PASS | 无匹配时返回 0 结果 |
| test_rg_scope_local | PASS | local 范围限制生效 |
| test_tfidf_requires_sklearn | PASS | 有 sklearn 时返回 tfidf 结果 |
| test_tfidf_insufficient_docs | PASS | 文档不足时优雅处理 |
| test_unknown_method | PASS | 未知方法返回 error |
| test_top_k_limit | PASS | top_k 截断生效 |

### 5. MCP Server 验证 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Tools 总数 | 20 | 全部注册 |
| 核心工具 | 齐全 | init/get/baseline/ascend/descend/check/search 等 |
| L4 新增工具 | 齐全 | se_check_consistency/se_store_consistency_report/se_search_proposals |

### 6. TUI 验证 ✅

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 导入 | 成功 | SEApp 类正常导入 |
| 实例化 | 成功 | 指定项目路径后正常实例化 |

## 修复记录

本轮测试中发现并修复了以下问题：

| 问题 | 原因 | 修复 |
|------|------|------|
| frontmatter content 重复传参 | read_layer_readme 返回的 dict 含 content 键，write_layer_readme 又接收 content 参数 | write_layer_readme 中过滤 metadata 的 content 键 |
| LLM prompt format 失败 | design_content 中含 `{` 被 str.format 误认为占位符 | 改用 safe string replacement (.replace) |
| search.py frontmatter strip 报错 | str.partition 只接受一个参数，传了 2 个 | 改用 str.split("---", 2) |
| text 检查器表头误提取 | 表格分隔行 "---" 被提取为符号 | 跳过含 "---" 的行 |
| datetime.utcnow() DeprecationWarning | Python 3.12 已废弃 | 全部替换为 datetime.now(timezone.utc) |

## 结论

**descent-1 全部核心功能通过测试，无阻塞性问题。L5 可以基线化。**

## descent-2 round 1（asc-001，2026-11-13）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-2 round 1 |
| 总用例数 | 45（新增 9：test_bootstrap.py 8 例 + test_consistency_llm.py 新增 2 例，其中 1 例为既有用例修正） |
| 通过 | 45 |
| 失败 | 0 |
| 命令 | `.venv/bin/python -m pytest tests/ -q` |

### 新增覆盖

| 用例组 | 结果 | 说明 |
|--------|------|------|
| test_bootstrap.py（8 例） | 8/8 PASS | 启动探测 3 路径（vinw-design 子目录/cwd/优先级）、无工程返回 None、adopt 模式（adopted=true/返回实际状态/空目录全新初始化） |
| test_code_root_from_manifest | PASS | manifest.code_root=".." 时符号在代码仓内匹配 |
| test_code_scope_supports_file_entry | PASS | code_scope 文件条目直扫 |

### MCP 端到端实测
- `se_check_consistency`(text, scope=vinw/)：20/20 匹配 → report-c88f12f4.md
- 自举加载：MCP 重启后自动接管 vinw-self-design（.vinw 路径）

## descent-3 round 1（asc-002 流程补救，2026-11-13）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-3 round 1 |
| 总用例数 | 52（新增 7：test_tui.py 4 例 + todo 轮次追踪 3 例） |
| 通过 | 52 |
| 失败 | 0 |

覆盖增量：TUI 渲染冒烟（含崩溃回归路径）、TUI 无工程分支、manifest 变更重渲染、TUI 瞬时错误韧性、todo_descent 写入/读取/回退。

## descent-4 round 1（asc-003 完成态迁移，2026-11-13）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-4 round 1 |
| 总用例数 | 55（新增 3：se_complete_project 成功/非 L7 拒绝/阻塞门控拒绝） |
| 通过 | 55 |
| 失败 | 0 |

## descent-5 round 1（asc-004 TUI 布局契约，2026-11-13）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-5 round 1 |
| 总用例数 | 56（test_tui.py 增至 5 例，新增真实滚动断言） |
| 通过 | 56 |
| 失败 | 0 |

关键新增：`test_todo_panel_is_actually_scrollable` —— 断言溢出时 `max_scroll_y > 0` 且 `scroll_end` 后 `scroll_y > 0`，直接锁死「固定高度 Static 无滚动内容」的回归路径。

实测（design 工程 110x32）：top/mid/bottom `max_scroll_y` = 18/39/49，滚动条常驻。

## descent-6 round 1（asc-005 结构修复，2026-11-13）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-6 round 1 |
| 总用例数 | 71（新增 tests/test_todo_lifecycle.py 15 例） |
| 通过 | 71 |
| 失败 | 0 |

### 新增覆盖（test_todo_lifecycle.py）

| 用例组 | 结果 | 说明 |
|--------|------|------|
| TestSectionHelpers (4) | PASS | 待办段提取/替换/缺失追加/占位符检测 |
| TestRollbackKeepsTodos (2) | PASS | 回滚保留现场待办与 todo_descent；README 缺失时回滚仍可用 |
| TestBaselinePlaceholderGuard (3) | PASS | 占位符拒绝基线；force 可跳过；真实待办后可基线 |
| TestPurgeConfirmations (3) | PASS | 结转旧轮次非阻塞门控、respect cutoff、无过期时幂等 |
| TestCompleteProjectGuards (3) | PASS | 占位符阻断完成；成功后回报 purged_confirmations；blocking 门控仍阻断 |

### 行为变更适配

基线守卫上线后，机制类旧用例（test_state_machine）改为显式 `force=True`，以保留对基线机制本身的覆盖。

## descent-7 round 1（asc-006 多项目跟踪管理，2026-11-13）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-7 round 1 |
| 总用例数 | 101（新增 test_registry.py 26 例 + TUI 多项目 4 例） |
| 通过 | 101 |
| 失败 | 0 |

### 按文件分布

| 文件 | 用例数 |
|------|--------|
| test_registry.py（新增） | 26 |
| test_todo_lifecycle.py | 15 |
| test_project.py | 13 |
| test_state_machine.py | 11 |
| test_bootstrap.py | 10 |
| test_consistency_llm.py | 10 |
| test_tui.py（含多项目 4 例） | 9 |
| test_search.py | 7 |
| **合计** | **101** |

### 多项目覆盖要点

| 用例组 | 结果 | 说明 |
|--------|------|------|
| TestRegistryBasics (8) | PASS | add/list/幂等/重名加后缀/remove 不动磁盘/损坏备份/原子写无残留 |
| TestStaleHandling (4) | PASS | missing 标记不删除、missing_since 记录、prune 默认 dry-run、force 才删 |
| TestResolution (5) | PASS | 路径/名称解析、未注册路径可用、失效与未知均抛 ProjectNotFound |
| TestPerToolProjectParam (5) | PASS | project 参数生效、不改变 _active_project、非法值返回 available_projects、None 保持旧行为 |
| TestRegistryTools (3) | PASS | register/list/remove、use_project 激活、prune 候选与执行 |
| TUI 多项目 (4) | PASS | 工作目录栏、选择器列出注册工程、切换后视图更新、按注册名启动 |

### 端到端实测
- MCP：`se_list_projects` 返回注册表；`se_get_project(project="vinw-self-design")` 正常；`se_register_project` 登记成功
- CLI：`vinw project add/list/prune` 全部正常
- 兼容性：`project=None` 路径零改动（旧用例 71 例全绿）

## descent-8 round 1（asc-007 注册表改 SQLite，2026-11-14）

| 指标 | 值 |
|------|-----|
| 测试轮次 | descent-8 round 1 |
| 总用例数 | 112（test_registry.py 由 26 → 37，+11） |
| 通过 | 112 |
| 失败 | 0 |

### 新增覆盖（SQLite 控制面）

| 用例组 | 结果 | 说明 |
|--------|------|------|
| TestSqliteControlPlane (8) | PASS | intent/observation 分离、非法 state 拒绝、事件历史、missing/recover 事件、touch 不重写全表、export 快照、**并发双写不丢更新** |
| 迁移与容错 (3) | PASS | 遗留 JSON 迁移且原文件保留为 `.migrated-*`、损坏库隔离为 `.corrupt-*` 不删除、WAL 模式断言 |

### 行为变更与测试适配
原 JSON 专属用例（损坏备份、原子写无 tmp）替换为 SQLite 语义用例（隔离重建、WAL 断言），断言意图不变。

### 端到端实测
- 真实 `~/.vinw/registry.json` 自动迁移为 `registry.db`，原文件保留；事件表记录 `import`
- CLI：`project add/list/deactivate/history/export` 全部正常
- MCP：`se_list_projects` 返回 `state`/`probed` 新字段，`se_set_project_state`、`se_project_history`、`se_export_projects` 可用

### 开发期自查发现并修复
`list()` 探测分支漏 `entries.append()` 导致 probe 路径返回空表——已修复并有测试覆盖。
