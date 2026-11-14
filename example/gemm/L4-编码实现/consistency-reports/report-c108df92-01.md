---
auditor: reviewer
auditor_model: independent-subagent
checked_at: '2026-11-14T08:26:28.851705+00:00'
code_fingerprint: 799a90fc7e581bbc12bcbbf205c42065289edea32f7447094acab130e82a15de
code_symbols_count: 43
descent: 3
design_hash: 69fb7430a986d9c513aff4762ed411cca89fd253583f64707c8018fb94bec8a2
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
  src/gemm_blocked.c: 6af93897e5c125aaf8b92cf99b1195ad59c907d0f76f4ac1479bb10fb49fd78e
  src/gemm_ref.c: e6c6bd2d4e306d8cd77a42b0c33128b4c41525437991116487ab2b2904a172b3
files_scanned: 4
gaps:
- analysis: R3/R4 两个 P0 无法自动判定
  classification: impl_bug
  confidence: high
  description: bench 只有一行 MT 门槛，无 gate-st（R3 单线程）与 gate-ext（R4 扩展性）
  design_ref: design-doc.md:122
  difference: 设计要求 ST+MT 两门槛行
  id: GAP-001
  impact: 验收不可复核
  missing: code
  recommendation: 分别测 1T/MT 并输出三条门槛
  severity: critical
  status: fixed
- analysis: 只读越界属 UB，普通分配掩盖
  classification: impl_bug
  confidence: high
  description: 奇数 K 尾部 pair load 越界读 64B（guard page 实测 SIGBUS）
  design_ref: implementation.md:49
  difference: 注释假设越界是下一行数据，但最后一行无下一行
  id: GAP-002
  impact: 页边界/硬化分配器下崩溃
  missing: code
  recommendation: 多分配哨兵行并清零
  severity: warning
  status: fixed
- analysis: 早期探针把数据装 Y[1] 却用 yoff=0 读 Y[0]
  classification: design_bug
  confidence: high
  description: 「单寄存器 ldx/ldy 无效，必须 pair load」被证伪：实测单寄存器正常
  design_ref: implementation.md:43
  difference: 文档 vs 实测相反
  id: GAP-003
  impact: 错误约束误导后续设计且直接引发 GAP-002
  missing: design
  recommendation: 更正三处文档
  severity: warning
  status: fixed
- analysis: 真实原因是首版整数移位 UB，已修
  classification: design_gap
  confidence: high
  description: 「-O3 必崩」用最终源码不可复现（17 次进程 0 崩溃）
  design_ref: implementation.md:45
  difference: 文档断言 vs 实测正常
  id: GAP-004
  impact: 文档可信度
  missing: test
  recommendation: 更正并移除 -O2 特例
  severity: warning
  status: fixed
- analysis: 设计-代码可追溯性断裂
  classification: design_gap
  confidence: high
  description: L3 无 AMX 设计章节，api-design 缺 4 个新符号，L2 无 corsix 出处
  design_ref: design-doc.md:101
  difference: 实现 136 行 + 4 符号无设计层记录
  id: GAP-005
  impact: L6/L7 无法一致性检查
  missing: design
  recommendation: 补 AMX 设计小节与接口，L2 补出处
  severity: warning
  status: fixed
- analysis: 属覆盖不足而非已知缺陷
  classification: design_gap
  confidence: high
  description: AMX 仅 5 个正例：缺回退分支、偶尾、大 K 正确性、EINVAL 断言、并发
  design_ref: test-results.md:35
  difference: 覆盖缺口（手工验证均通过）
  id: GAP-006
  impact: 回归保护缺失
  missing: test
  recommendation: 并入测试
  severity: warning
  status: open
gaps_count: 6
inconsistencies:
- category: logic
  code_ref: bench/bench_gemm.c
  description: R3 定义为单线程 8×，但 bench/L5 用 MT 比值判 PASS，ST 从未判定
  design_ref: proposals.md:20
  id: INC-001
  severity: null
  suggestion: 机器可判定的两条门槛
- category: data_model
  code_ref: implementation.md:58
  description: 跨层性能数字未标尺寸/线程，3.56 与 1.74 混用导致阈值差 2 倍
  design_ref: synthesis.md:51
  id: INC-002
  severity: null
  suggestion: 统一标注与门槛尺寸
- category: interface
  code_ref: include/gemm.h
  description: api-design 只列 6 个符号，头文件已 10 个；构建产物表过期
  design_ref: api-design.md:17
  id: INC-003
  severity: null
  suggestion: 同步接口与构建布局
- category: logic
  code_ref: bench/bench_gemm.c:61
  description: setenv 空串+overwrite=0 语义错误，线程数由环境偶然决定
  design_ref: design-doc.md:122
  id: INC-004
  severity: null
  suggestion: 显式设置/恢复并打印实际线程
- category: logic
  code_ref: null
  description: 「8B/FLOP × 23.64 = 47 GB/s」算术错误
  design_ref: synthesis.md:60
  id: INC-005
  severity: null
  suggestion: 改为 2B/FLOP 或 189 GB/s
inconsistencies_count: 5
kind: llm
layer: L4-编码实现
llm_verdict: warning
overall_status: warning
policy: text+llm
report_id: c108df92-01
se_version: '2.0'
triage:
- analysis: 已补三条门槛与显式线程控制
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: bench 输出 gate-st/gate-mt/gate-ext 三条门槛并显式控制线程
  design_ref: null
  difference: 缺 gate-st/gate-ext
  finding_id: GAP-001
  id: GAP-001
  impact: 验收可判定
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已加哨兵行
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: B 打包多分配哨兵行并清零，消除奇数 K 越界
  design_ref: null
  difference: 奇数 K 尾部越界
  finding_id: GAP-002
  id: GAP-002
  impact: 消除 UB
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已在代码/设计/L4/L5 三处更正
  classification: design_bug
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: 三处文档更正：单寄存器 load 同样可用
  design_ref: null
  difference: pair-load 结论错误
  finding_id: GAP-003
  id: GAP-003
  impact: 消除错误约束
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 根因是首版 shift UB；已修并移除 -O2 特例
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 根因是首版整数移位 UB；已修并移除 -O2 特例，-O3 验证通过
  design_ref: null
  difference: -O3 结论不可复现
  finding_id: GAP-004
  id: GAP-004
  impact: 文档可信度恢复
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已补 AMX 设计小节 + 接口 + 构建布局
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: L3 补 AMX 设计小节与接口，L2 补出处，构建布局更新
  design_ref: null
  difference: L3 无 AMX 设计
  finding_id: GAP-005
  id: GAP-005
  impact: 可追溯性恢复
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 回退/偶尾/大 K/EINVAL/并发 缺仓库内用例；手工验证均正确
  classification: design_gap
  code_ref: null
  confidence: high
  decision: accept_as_is
  decision_note: 回退/偶尾/大K/EINVAL/并发用例延后到下轮（手工已验证正确）
  design_ref: null
  difference: AMX 覆盖不足
  finding_id: GAP-006
  id: GAP-006
  impact: 回归保护
  kind: inconsistency
  recommendation: 下轮补测（非阻塞）
  severity: warning
  status: accepted
- analysis: 已统一 1024³ 口径并输出 gate-st
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: R3 单线程门槛已可机器判定（gate-st 19.9-24.8× PASS）
  design_ref: null
  difference: ST 门槛未判定
  finding_id: INC-001
  id: INC-001
  impact: 验收可复核
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已统一标注尺寸/线程并互引
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: 统一 1024³ 同尺寸单线程基线并标注线程/尺寸
  design_ref: null
  difference: 数字口径不一致
  finding_id: INC-002
  id: INC-002
  impact: 阈值清晰
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: api-design 已补 4 符号与构建布局
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: api-design 补 4 个符号与 build/build-amx 布局
  design_ref: null
  difference: 接口表过期
  finding_id: INC-003
  id: INC-003
  impact: 接口基线恢复
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
- analysis: 已改为显式 setenv/restore + 打印实际线程
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 线程 env 显式设置/恢复并打印实际线程数
  design_ref: null
  difference: 线程语义错误
  finding_id: INC-004
  id: INC-004
  impact: bench 稳定
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已改为 2B/FLOP≈47GB/s
  classification: design_bug
  code_ref: null
  confidence: high
  decision: fix_design
  decision_note: L2 算术已更正为 2B/FLOP ≈47GB/s
  design_ref: null
  difference: 8B/FLOP 算术错误
  finding_id: INC-005
  id: INC-005
  impact: 论证可信
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: decided
triage_counts:
  by_classification:
    design_bug: 2
    design_gap: 5
    impl_bug: 4
  open: 0
  total: 11
---

# 一致性检查报告 (c108df92-01)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 5 |
| 匹配项 | 6 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | - | logic | proposals.md:20 | bench/bench_gemm.c | R3 定义为单线程 8×，但 bench/L5 用 MT 比值判 PASS，ST 从未判定 | 机器可判定的两条门槛 |
| INC-002 | - | data_model | synthesis.md:51 | implementation.md:58 | 跨层性能数字未标尺寸/线程，3.56 与 1.74 混用导致阈值差 2 倍 | 统一标注与门槛尺寸 |
| INC-003 | - | interface | api-design.md:17 | include/gemm.h | api-design 只列 6 个符号，头文件已 10 个；构建产物表过期 | 同步接口与构建布局 |
| INC-004 | - | logic | design-doc.md:122 | bench/bench_gemm.c:61 | setenv 空串+overwrite=0 语义错误，线程数由环境偶然决定 | 显式设置/恢复并打印实际线程 |
| INC-005 | - | logic | synthesis.md:60 | - | 「8B/FLOP × 23.64 = 47 GB/s」算术错误 | 改为 2B/FLOP 或 189 GB/s |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| implementation.md:42 | src/amx_asm.h | AMX 指令编码 | 与 corsix/amx 规格逐位一致 |
| implementation.md:49 | src/gemm_amx.c | amx_tile 相位映射 | 四相位 z_row=t、yoff=t*64、stz 行 j*4+t 与模拟器公式一致 |
| implementation.md:50 | src/gemm_amx.c | B 块状打包 | 64B/k 行与 pair load 连续性假设吻合 |
| test-results.md:33 | tests/test_gemm.c | 586/591 | 两种构建模式复现一致 |
| Makefile | Makefile | 双构建目录 | build/ 与 build-amx/ 隔离，切换模式不再假通过 |
| implementation.md:52 | src/gemm_amx.c | 未编译回退 | 符号存在 + EINVAL + bench 守卫 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->