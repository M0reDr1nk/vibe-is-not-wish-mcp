---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "consistency-report"
report_id: "L4-r1-text"
checked_at: "2026-11-13T10:54:46.024364+00:00"
overall_status: "warning"
---

# 一致性检查报告 (L4-r1-text)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 20 |
| 匹配项 | 0 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | warning | missing | table L24 | N/A | Design symbol 'layer' not found in code | Implement layer or update design doc |
| INC-002 | warning | missing | api ref L16 | N/A | Design symbol 'se_init_project' not found in code | Implement se_init_project or update design doc |
| INC-003 | warning | missing | api ref L17 | N/A | Design symbol 'se_get_project' not found in code | Implement se_get_project or update design doc |
| INC-004 | warning | missing | api ref L23 | N/A | Design symbol 'se_baseline' not found in code | Implement se_baseline or update design doc |
| INC-005 | warning | missing | api ref L24 | N/A | Design symbol 'se_list_baselines' not found in code | Implement se_list_baselines or update design doc |
| INC-006 | warning | missing | api ref L30 | N/A | Design symbol 'se_ascend' not found in code | Implement se_ascend or update design doc |
| INC-007 | warning | missing | api ref L31 | N/A | Design symbol 'se_descend' not found in code | Implement se_descend or update design doc |
| INC-008 | warning | missing | api ref L32 | N/A | Design symbol 'se_can_descend' not found in code | Implement se_can_descend or update design doc |
| INC-009 | warning | missing | api ref L38 | N/A | Design symbol 'se_require_confirmation' not found in code | Implement se_require_confirmation or update design doc |
| INC-010 | warning | missing | api ref L39 | N/A | Design symbol 'se_resolve_confirmation' not found in code | Implement se_resolve_confirmation or update design doc |
| INC-011 | warning | missing | api ref L45 | N/A | Design symbol 'se_store_document' not found in code | Implement se_store_document or update design doc |
| INC-012 | warning | missing | api ref L46 | N/A | Design symbol 'se_read_document' not found in code | Implement se_read_document or update design doc |
| INC-013 | warning | missing | api ref L47 | N/A | Design symbol 'se_list_documents' not found in code | Implement se_list_documents or update design doc |
| INC-014 | warning | missing | api ref L53 | N/A | Design symbol 'se_log_change' not found in code | Implement se_log_change or update design doc |
| INC-015 | warning | missing | api ref L54 | N/A | Design symbol 'se_get_changelog' not found in code | Implement se_get_changelog or update design doc |
| INC-016 | warning | missing | api ref L60 | N/A | Design symbol 'se_check_consistency' not found in code | Implement se_check_consistency or update design doc |
| INC-017 | warning | missing | api ref L73 | N/A | Design symbol 'se_search_proposals' not found in code | Implement se_search_proposals or update design doc |
| INC-018 | warning | missing | api ref L87 | N/A | Design symbol 'se_get_todos' not found in code | Implement se_get_todos or update design doc |
| INC-019 | warning | missing | api ref L88 | N/A | Design symbol 'se_update_todo' not found in code | Implement se_update_todo or update design doc |
| INC-020 | warning | missing | api ref L94 | N/A | Design symbol 'se_get_next_steps' not found in code | Implement se_get_next_steps or update design doc |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| — | — | — | — |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->
