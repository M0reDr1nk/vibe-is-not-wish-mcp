---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "consistency-report"
report_id: "5ec481bb"
checked_at: "2026-11-13T16:52:38.519138+00:00"
overall_status: "passed"
---

# 一致性检查报告 (5ec481bb)

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
| api-design.md v0.7 全部工具 | vinw/server.py | 23 个 se_* 工具（含 5 个注册表工具） | text 方法 28/28 符号匹配 |
| 注册表契约 | vinw/store/registry.py | ProjectRegistry | JSON 原子写/探测/prune/resolve 全部实现 |
| TUI 契约 | vinw/tui/app.py + selector.py | ProjectSelector / action_select_project | 工作目录栏+选择器+p 键切换 |
| CLI 契约 | vinw/__main__.py | project add/list/remove/prune | 实测通过 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->
