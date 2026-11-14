---
checked_at: '2026-11-13T17:37:53.422691+00:00'
code_fingerprint: c252953f5ae4c88eea06192f9e647d9c5c859b70e616e29a25aa782683b18878
descent: 2
design_hash: aa99d6d2d3dfdfc6ae8df634f0d13444c9ba6d5b17ccad2e83c1dfc65c9e26d0
doc_type: consistency-report
layer: L4-编码实现
overall_status: warning
report_id: 7366f67f
se_version: '2.0'
---

# 一致性检查报告 (7366f67f)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 2 |
| 匹配项 | 0 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | warning | missing | code block L13 | N/A | Design symbol 'GEMM_H' not found in code | Implement GEMM_H or update design doc |
| INC-002 | warning | missing | code block L18 | N/A | Design symbol 'enum' not found in code | Implement enum or update design doc |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| — | — | — | — |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->