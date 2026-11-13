---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "consistency-report"
report_id: "3fbe9edf"
checked_at: "2026-11-13T16:40:13.040464+00:00"
overall_status: "passed"
---

# 一致性检查报告 (3fbe9edf)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | passed |
| 不一致项 | 0 |
| 匹配项 | 4 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| — | — | — | — | — | 无不一致项 | — |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| api-design.md 工具清单 (v0.6) | vinw/server.py | 18 个 se_* MCP 工具（新增 se_purge_confirmations） | text 方法 22/22 匹配 |
| 待办生命周期契约 | vinw/store/project.py | extract_todo_section/replace_todo_section/rollback_to_baseline | 回滚保留现场待办段与 todo_descent |
| 基线占位符守卫 | vinw/workflow/state_machine.py | baseline(force) | 占位符拒绝基线，force 可跳过 |
| 门控清理 | vinw/workflow/state_machine.py | purge_confirmations | se_purge_confirmations + complete 自动结算非阻塞过期门控 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->
