---
auditor: reviewer
auditor_model: independent-subagent
checked_at: '2026-11-14T09:30:40.213593+00:00'
code_fingerprint: 8ff363515627b6726b344f88611a3f1034b32954b0bad3209b724d5c779ed8bc
code_symbols_count: 45
descent: 4
design_hash: 936c049147d721b1a2e2c1b863c371e17e85f7444ea05f2d27f58cfef53b30bc
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
  src/gemm_blocked.c: 0813a2b1026e0d9dbbfe56399e4be824f60ece62987dbf2007c46fb7c8f62a78
  src/gemm_ref.c: e6c6bd2d4e306d8cd77a42b0c33128b4c41525437991116487ab2b2904a172b3
files_scanned: 4
gaps:
- analysis: 先有代码后补设计，属本轮流程违规
  classification: design_gap
  confidence: high
  description: L3 v004 仍以 MC=64 与 round 边界为冻结设计，实现已回退 MC=128 并换分配算法，设计层未同步（design_lag）
  design_ref: design-doc.md:181
  difference: 设计 vs 实现
  id: GAP-001
  impact: 一致性门禁对新代码失效
  missing: design
  recommendation: 更新 L3：D1 标注被证伪、D3 换为实际算法
  severity: warning
  status: fixed
- analysis: 外部 harness 穷举验证无重叠/遗漏，但仓库无保护
  classification: design_gap
  confidence: high
  description: parallel_for_m/core_weights 无任何仓库内测试；加权分支从未被覆盖
  design_ref: tests/test_gemm.c:47
  difference: 60 行新逻辑零测试
  id: GAP-002
  impact: 后续改动静默破坏分配
  missing: test
  recommendation: 补端到端覆盖用例
  severity: warning
  status: fixed
- analysis: 4.34 来自 descent-2 前测
  classification: design_gap
  confidence: high
  description: 「同一二进制 2.53~4.34×」不成立（4.34 属旧二进制）；L1 仍写 4.34× 已达标
  design_ref: implementation.md:86
  difference: 方差声明不可审计
  id: GAP-003
  impact: R4 结论稳定性
  missing: test
  recommendation: 改写并清理 L1 残留
  severity: warning
  status: fixed
gaps_count: 3
inconsistencies:
- category: logic
  code_ref: gemm_blocked.c:207
  description: D3 的 round 公式会重现 0 块 bug，与实现不符
  design_ref: design-doc.md:203
  id: INC-001
  severity: null
  suggestion: 改为实际算法
- category: logic
  code_ref: gemm_blocked.c:207
  description: 加权分配在 nb=16/nt=8（目标场景）退化为等分，加权从未生效
  design_ref: design-doc.md:186
  id: INC-002
  severity: null
  suggestion: 按理想块数分配或标注未验证
- category: data_model
  code_ref: gemm_blocked.c:175
  description: perflevel1 探测为死代码；(void)ne 掩盖
  design_ref: design-doc.md:188
  id: INC-003
  severity: null
  suggestion: 用 ne 或删除
- category: logic
  code_ref: gemm_blocked.c:198
  description: nt>32 clamp 在越界检查之后 → share[32] 栈溢出（潜在）
  design_ref: api-design.md:53
  id: INC-004
  severity: null
  suggestion: 先 clamp 再检查
- category: data_model
  code_ref: bench_gemm.c:85
  description: bench 打印 threads=8 但实际是 min(threads,nblocks)
  design_ref: test-results.md:66
  id: INC-005
  severity: null
  suggestion: 按实际值输出
- category: constraint
  code_ref: gemm_blocked.c:169
  description: sysctl 无平台守卫，非 Apple 平台编译失败，与 R6 可移植声称冲突
  design_ref: design-doc.md:69
  id: INC-006
  severity: null
  suggestion: 加 __APPLE__ 守卫 + 等权回退
inconsistencies_count: 6
kind: llm
layer: L4-编码实现
llm_verdict: warning
overall_status: warning
policy: text+llm
report_id: 5dffb92d-01
se_version: '2.0'
triage:
- analysis: 已更新 L3：D1 标注被证伪、D3 换实际算法
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: L3 已更新 D1/D3
  design_ref: null
  difference: 设计未同步回退
  finding_id: GAP-001
  id: GAP-001
  impact: 可追溯性
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 已补 4096×64×32、2048×48×64 覆盖性用例（588 例）
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 2 例覆盖性用例
  design_ref: null
  difference: 无分配测试
  finding_id: GAP-002
  id: GAP-002
  impact: 回归保护
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已改写并清理 L1 的 4.34× 残留
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: 方差声明改写 + L1 清理
  design_ref: null
  difference: 方差声明不成立
  finding_id: GAP-003
  id: GAP-003
  impact: 可审计
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 设计已改为实际算法
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: D3 已换实际算法
  design_ref: null
  difference: D3 公式会复现 0 块 bug
  finding_id: INC-001
  id: INC-001
  impact: 避免误导
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 已重写为理想块数分配；并诚实标注：MC=128 时 nb==nt，加权仍为空操作
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 加权分配重写 + 诚实标注为空操作
  design_ref: null
  difference: 加权在目标场景退化
  finding_id: INC-002
  id: INC-002
  impact: 结论已纠正
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已删除 perflevel1 探测
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 死代码已删
  design_ref: null
  difference: 死代码
  finding_id: INC-003
  id: INC-003
  impact: 代码清晰
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: clamp 已前置
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: clamp 前置
  design_ref: null
  difference: 潜在栈溢出
  finding_id: INC-004
  id: INC-004
  impact: 潜在 UB 消除
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已按 min(threads,blocks) 输出
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 线程标签按实际值
  design_ref: null
  difference: 线程标签错误
  finding_id: INC-005
  id: INC-005
  impact: 测量可信
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已加 __APPLE__ 守卫与等权回退
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 平台守卫 + 等权回退
  design_ref: null
  difference: 平台无守卫
  finding_id: INC-006
  id: INC-006
  impact: 跨平台可编译
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
triage_counts:
  by_classification:
    design_gap: 4
    impl_bug: 5
  open: 0
  total: 9
---

# 一致性检查报告 (5dffb92d-01)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 6 |
| 匹配项 | 4 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | - | logic | design-doc.md:203 | gemm_blocked.c:207 | D3 的 round 公式会重现 0 块 bug，与实现不符 | 改为实际算法 |
| INC-002 | - | logic | design-doc.md:186 | gemm_blocked.c:207 | 加权分配在 nb=16/nt=8（目标场景）退化为等分，加权从未生效 | 按理想块数分配或标注未验证 |
| INC-003 | - | data_model | design-doc.md:188 | gemm_blocked.c:175 | perflevel1 探测为死代码；(void)ne 掩盖 | 用 ne 或删除 |
| INC-004 | - | logic | api-design.md:53 | gemm_blocked.c:198 | nt>32 clamp 在越界检查之后 → share[32] 栈溢出（潜在） | 先 clamp 再检查 |
| INC-005 | - | data_model | test-results.md:66 | bench_gemm.c:85 | bench 打印 threads=8 但实际是 min(threads,nblocks) | 按实际值输出 |
| INC-006 | - | constraint | design-doc.md:69 | gemm_blocked.c:169 | sysctl 无平台守卫，非 Apple 平台编译失败，与 R6 可移植声称冲突 | 加 __APPLE__ 守卫 + 等权回退 |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| design-doc.md:188 | gemm_blocked.c:183 | 权重 P=2/E=1 | 本机 np=4，权重 [2,2,2,2,1,1,1,1] 与设计一致 |
| design-doc.md:61 | gemm_blocked.c:264 | 线程数 min(threads,nblocks) | 成立 |
| implementation.md:78 | gemm_blocked.c:210 | 保底 1 块 | 穷举验证区间无重叠/遗漏 |
| test-results.md:73 | - | 588/593 | 新增 2 例覆盖性用例后实测 588/593 全绿 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->