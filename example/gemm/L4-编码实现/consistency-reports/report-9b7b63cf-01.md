---
auditor: self
auditor_model: 'self-audit (independent reviewers failed: reviewer20 no output, reviewer21
  no output, r22 timeout)'
checked_at: '2026-11-14T12:41:15.076030+00:00'
code_fingerprint: 119f123f5db7debecf790334095b0b4b7401edd8d3985b8f9600859b4565bc14
code_symbols_count: 46
descent: 5
design_hash: fe3b082b7f3c1231de88b66701357cb099827356bc52af7c1fb74d8cec7ec9b8
design_hash_algo: layer-v1
doc_type: consistency-report
extensions:
- .py
- .c
- .h
- .cc
- .cpp
- .hpp
- .rs
- .go
- .java
- .ts
- .tsx
- .js
file_hashes:
  src/amx_asm.h: 90bf64b865b4cb4421265df9d08f168789d5ae8d7cc51257d1b3ebf174881d77
  src/gemm_amx.c: fc7f4fd40a2c593f6e5557427e7d122d55a81e70376e9b1f7f9cf77c7b53aaac
  src/gemm_blocked.c: e4f403ca69cbec93ed526405bf8f1eb6a6ec51c273adbc60ab9aef24e267809b
  src/gemm_ref.c: e6c6bd2d4e306d8cd77a42b0c33128b4c41525437991116487ab2b2904a172b3
files_scanned: 4
gaps:
- analysis: 显式强制 NEON 的入口语义上应走分块路径；对 bench 各尺寸无影响（256³ == 阈值，不触发捷径）
  classification: design_gap
  confidence: high
  description: gemm_f32_neon 不走小矩阵捷径，设计未规定该语义
  design_ref: design-doc.md (descent-5 §1)
  difference: gemm_f32 对小矩阵走 gemm_f32_small；gemm_f32_neon 直接进 blocked 路径
  id: GAP-001
  impact: 极小矩阵经该入口会慢但结果正确
  missing: design
  recommendation: 在设计写明该语义与调用建议
  severity: warning
  status: fixed
gaps_count: 1
inconsistencies:
- category: interface
  code_ref: bench/bench_gemm.c:196
  description: gate-delivery 计算方式未指明 base_ijk 是单线程基线
  design_ref: design-doc.md (descent-5 §2)
  id: INC-001
  severity: null
  suggestion: 已确认为 naive-ijk 单线程 GFLOPS，与 gate-st 同口径
inconsistencies_count: 1
kind: llm
layer: L4-编码实现
llm_verdict: warning
overall_status: warning
policy: text+llm
report_id: 9b7b63cf-01
se_version: '2.0'
triage:
- analysis: 已在 design-doc 写明：gemm_f32_neon 强制分块路径、不走小矩阵捷径
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: design-doc 已写明 gemm_f32_neon 语义
  design_ref: null
  difference: 捷径语义未规定
  finding_id: GAP-001
  id: GAP-001
  impact: 语义明确
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 已确认 base_ijk 为单线程基线，无需改代码
  classification: design_gap
  code_ref: null
  confidence: high
  decision: accept_as_is
  decision_note: 代码 base_ijk 已是单线程基线，无需改
  design_ref: null
  difference: 文档略写
  finding_id: INC-001
  id: INC-001
  impact: 无
  kind: inconsistency
  recommendation: accept_as_is
  severity: warning
  status: accepted
triage_counts:
  by_classification:
    design_gap: 2
  open: 0
  total: 2
---

# 一致性检查报告 (9b7b63cf-01)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 1 |
| 匹配项 | 8 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | - | interface | design-doc.md (descent-5 §2) | bench/bench_gemm.c:196 | gate-delivery 计算方式未指明 base_ijk 是单线程基线 | 已确认为 naive-ijk 单线程 GFLOPS，与 gate-st 同口径 |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| design-doc.md (descent-5 §1) | src/gemm_blocked.c gemm_f32 | 路由 | 参数校验→小矩阵→AMX→NEON 回退，与设计逐条一致 |
| design-doc.md (descent-5 §1) | src/gemm_blocked.c gemm_f32 | AMX 失败回退 | st != GEMM_OK 时落到 gemm_f32_neon；blocked 路径全量写 C，不会残留部分结果 |
| design-doc.md (descent-5 §2) | bench/bench_gemm.c | vinw-neon / vinw-delivery | 前者强制 gemm_f32_neon，后者 gemm_f32，与设计一致 |
| design-doc.md (descent-5 §2) | bench/bench_gemm.c:196 | gate-delivery | delivery_g / base_ijk（naive-ijk 单线程），门槛 4x |
| design-doc.md (descent-5 §2) | bench/bench_gemm.c:50 | effective_threads_for | min(threads,32,ceil(M/MC))，与库内实际线程数一致 |
| L1 R4 修订 | bench/bench_gemm.c:201 | gate-st/gate-ext | gate-st 门槛 8x 保留，gate-ext 标注参考，与 L1 修订一致 |
| L1 复杂度边界 | src/gemm_blocked.c / src/gemm_amx.c | 无新增复杂后端 | 未引入多线程 AMX、fp16/bf16、多级阻塞重写 |
| L5 descent-5 | - | 588/593 | 两种构建全绿（作者实测） |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->