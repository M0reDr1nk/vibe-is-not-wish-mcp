---
checked_at: '2026-11-14T12:59:25.168064+00:00'
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
kind: text
layer: L4-编码实现
overall_status: passed
policy: text+llm
report_id: ac246cbf-01
se_version: '2.0'
---

# 一致性检查报告 (ac246cbf-01)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | passed |
| 不一致项 | 0 |
| 匹配项 | 8 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| — | — | — | — | — | 无不一致项 | — |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| api-design.md:81 | src/gemm_amx.c:62 | gemm_amx | Symbol defined in code |
| api-design.md:81 | src/gemm_amx.c:24 | gemm_amx_available | Symbol defined in code |
| api-design.md:51 | src/gemm_blocked.c:318 | gemm_blocked_1t | Symbol defined in code |
| api-design.md:52 | src/gemm_blocked.c:249 | gemm_blocked_par | Symbol defined in code |
| api-design.md:50 | src/gemm_blocked.c:79 | macro_kernel | Symbol defined in code |
| api-design.md:48 | src/gemm_blocked.c:49 | pack_a | Symbol defined in code |
| api-design.md:49 | src/gemm_blocked.c:63 | pack_b | Symbol defined in code |
| api-design.md:53 | src/gemm_blocked.c:200 | parallel_for_m | Symbol defined in code |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->