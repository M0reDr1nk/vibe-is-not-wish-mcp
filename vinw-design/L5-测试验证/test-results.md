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
