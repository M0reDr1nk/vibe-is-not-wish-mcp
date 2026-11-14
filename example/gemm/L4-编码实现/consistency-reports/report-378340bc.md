---
checked_at: '2026-11-13T18:05:56.170574+00:00'
code_fingerprint: e408575ea67aab34ca560b291b9bf65cf8a52d7b16c369203d97961d9e273d93
descent: 2
design_hash: aa99d6d2d3dfdfc6ae8df634f0d13444c9ba6d5b17ccad2e83c1dfc65c9e26d0
doc_type: consistency-report
file_hashes:
  src/gemm_blocked.c: a6b892b268a2671149673e1aeb5d0de6d4419ac79a71e1ac38a8e3dcb3c2b8ca
  src/gemm_ref.c: f0b8aacb7ed7033612dffc77545233cae683ed95134dde24ec106b1413fa4607
kind: text
layer: L4-编码实现
overall_status: warning
policy: text+llm
report_id: 378340bc
se_version: '2.0'
---

# 一致性检查报告 (378340bc)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 2 |
| 匹配项 | 4 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | warning | missing | api-design.md | N/A | Design symbol 'gemm_blocked_1t' not found in code | Implement gemm_blocked_1t or remove it from the design doc |
| INC-002 | warning | missing | api-design.md | N/A | Design symbol 'macro_kernel' not found in code | Implement macro_kernel or remove it from the design doc |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| api-design.md | src/gemm_blocked.c | gemm_blocked_par | Symbol defined in code |
| api-design.md | src/gemm_blocked.c | pack_a | Symbol defined in code |
| api-design.md | src/gemm_blocked.c | pack_b | Symbol defined in code |
| api-design.md | src/gemm_blocked.c | parallel_for_m | Symbol defined in code |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->