---
ascent_history:
- created_at: '2026-11-13T17:36:31.068879+00:00'
  descent_after: 2
  descent_before: 1
  from_layer: L4-编码实现
  id: asc-001
  reason: 环境实测 Apple clang 21 不支持 -fopenmp 且无 libomp，L3 v001 的 OpenMP 并行设计无法落地；上升改设计为
    pthreads 主实现 + OpenMP 可选
  to_baseline: v001
  to_layer: L3-方案细化
- created_at: '2026-11-14T07:24:46.152850+00:00'
  descent_after: 3
  descent_before: 2
  from_layer: L4-编码实现
  id: asc-002
  reason: R3/验收条款「相对 naive ikj ≥8×」经验证不可达：bench 基线 ikj 单线程已达 23.64 GFLOPS≈单核 NEON
    峰值(25.6)，8×=189 GFLOPS≈整机峰值；而真·朴素 ijk 仅 3.56 GFLOPS（相对可达 30×）。需回 L1 重新定义性能基线口径
  to_baseline: v001
  to_layer: L1-需求拆解
- created_at: '2026-11-14T08:53:37.127671+00:00'
  descent_after: 4
  descent_before: 3
  from_layer: L7-终验
  id: asc-003
  reason: R4 扩展性实测 3.22× 未达 4× 门槛：需改设计为 MC=64 细粒度 + 按 perflevel 加权分块，消除 E 核尾延迟
  to_baseline: v003
  to_layer: L3-方案细化
completed_at: '2026-11-14T09:31:25.298593+00:00'
created_at: '2026-11-13T17:28:57.208978+00:00'
current_descent: 4
current_layer: L7-终验
descent_started_at: '2026-11-14T08:53:37.128569+00:00'
description: 本机 CPU GEMM 加速实现（NEON/多线程/分块），含正确性测试与性能基准
layer_states:
  L1-需求拆解:
    active_ascent: asc-002
    baselined_at: '2026-11-14T08:26:54.271764+00:00'
    descent_count: 2
    latest_baseline: v002
    status: baselined
  L2-参考文献与方案搜证汇总:
    baselined_at: '2026-11-14T08:27:04.922050+00:00'
    descent_count: 2
    latest_baseline: v002
    status: baselined
  L3-方案细化:
    active_ascent: asc-003
    baselined_at: '2026-11-14T09:30:54.479228+00:00'
    descent_count: 4
    latest_baseline: v004
    status: baselined
  L4-编码实现:
    audit:
      auto_fixable: []
      auto_fixable_count: 0
      decision: resolved
      escalations: []
      escalations_count: 0
      findings: 9
      report_id: 5dffb92d-01
    baselined_at: '2026-11-14T09:30:59.021288+00:00'
    consistency:
      checked_at: '2026-11-14T09:30:59.015940+00:00'
      code_fingerprint: 8ff363515627b6726b344f88611a3f1034b32954b0bad3209b724d5c779ed8bc
      descent: 4
      design_hash: 936c049147d721b1a2e2c1b863c371e17e85f7444ea05f2d27f58cfef53b30bc
      design_hash_algo: layer-v1
      llm_auditor: reviewer
      llm_report_id: 5dffb92d-01
      llm_verdict: warning
      overall: passed
      report_id: 9a884b54-01
    descent_count: 4
    latest_baseline: v002
    status: baselined
  L5-测试验证:
    baselined_at: '2026-11-14T09:31:08.009653+00:00'
    descent_count: 2
    latest_baseline: v002
    status: baselined
  L6-检视清理:
    baselined_at: '2026-11-14T09:31:12.319181+00:00'
    descent_count: 2
    latest_baseline: v002
    status: baselined
  L7-终验:
    completed_at: '2026-11-14T09:31:25.298593+00:00'
    descent_count: 2
    latest_baseline: null
    status: completed
name: gemm
pending_confirmations:
- blocking: true
  descent: 1
  description: L1 需求拆解确认：GEMM 本机 CPU 加速拆为 R1-R7（C 接口 / 正确性对比 / 单线程分块 / OpenMP 多线程
    / 基准对比 Accelerate / arm64+x86 可移植 / make 构建），非目标明确排除 FP16/GPU/batched/转置，验收为 make
    test 通过 + make bench 8x 加速门槛。请确认范围是否符合预期。
  feedback: 批准 R1-R7 范围与非目标。附带意见：需在 VINW 自身 backlog 记录"对模糊需求反向提问使其清晰化"能力（已记入 vinw-self-design
    L1 待办与 proposals.md descent-10 候选需求 C1-C5）。
  id: cfm-20261113-172916-001
  item_type: requirement-decomposition
  layer: L1-需求拆解
  options:
  - approve
  - reject
  - modify
  proposed_at: '2026-11-13T17:29:16.331203+00:00'
  resolution: approve
  resolved_at: '2026-11-13T17:32:38.101312+00:00'
- blocking: false
  descent: 1
  description: L2 搜证结论确认 + 3 个关键歧义待澄清：A1 是否允许调用 Accelerate 作为交付实现（推荐手写，Accelerate
    仅作对照）；A2 精度是否仅 float32（推荐是）；A3 目标规模（推荐中大规模 512-4096，小矩阵简化路径）。五项技术选型：Goto/BLIS
    路线三层分块+打包+4x8微内核、编译器自动向量化、按 M 行块 OpenMP 并行、MC=128/KC=256/NC=2048、相对容差 1e-3。
  feedback: A1 手写实现（Accelerate 仅作 bench 对照）；A2 仅 float32；A3 中大规模 512-4096（小矩阵走简化路径）。五项技术选型全部接受。
  id: cfm-20261113-173304-002
  item_type: ambiguity-clarification
  layer: L2-参考文献与方案搜证汇总
  options:
  - approve
  - reject
  - modify
  proposed_at: '2026-11-13T17:33:04.104243+00:00'
  resolution: approve
  resolved_at: '2026-11-13T17:33:39.585184+00:00'
- assumption: R3 的「相对 naive ikj ≥8×」中，基线指 bench 现有的 naive-ikj（ikj 循环序、全向量化，实测单线程 23.64
    GFLOPS）。若按此口径，8× = 189 GFLOPS，接近 M3 整机 NEON 峰值（8 核 ×25.6），纯 C 实现不可达。
  blocking: true
  context: descent-3 实测（Apple M3，4P+4E）：真·朴素 ijk 3.56 GFLOPS / ikj 23.64 GFLOPS（≈单核峰值）/
    当前 blocked 单线程 25.14、8 线程 109.19（vs ikj 3.9×，vs ijk 30.6×）。Accelerate 1597 GFLOPS
    来自 AMX 协处理器，纯 C/NEON 不可比。
  corrected: true
  descent: 3
  description: GEMM 性能验收基线应如何定义？当前 bench 的「naive-ikj」实测已达单核硬件峰值，8× 不可达。
  deviation: 若基线本意为真·朴素 ijk，则交付当前已大幅超 8×（单线程 7.06×，略低于 8×；8 线程 30.6×）；若坚持 ikj 口径，则需求需改为可达目标（约
    4~5×），否则永远无法验收。
  feedback: 按推荐选择双基线方案：验收门槛用真·朴素 ijk（≥8×），ikj 作为性能上限参照展示
  id: cfm-20261114-072455-003
  item_type: clarification
  layer: L1-需求拆解
  options:
  - description: bench 增加 ijk 参考实现（内部步长 N 的经典朴素版），性能条款改为「相对朴素 ijk ≥8×」，单线程与多线程分别验收
    id: ijk-baseline
    impact: 当前已 30.6×（MT）/7.06×（ST），只需微调 ST 使其过 8×，需求立即可达
    label: 基线改为真·朴素 ijk
  - description: 承认 ikj 基线已接近硬件峰值，条款改为「相对 ikj ≥4×」（MT）
    id: ikj-lower-4x
    impact: 当前 3.9× 已接近，小幅优化即可达标；但单线程 1.06× 无法宣称加速
    label: 保留 ikj 基线但降至 4×
  - description: 不再相对比较，改为「1024³ ≥120 GFLOPS（8 线程）、单线程 ≥24 GFLOPS」
    id: absolute-gflops
    impact: 目标清晰可验，需继续优化线程扩展（当前 109）
    label: 改为绝对性能目标
  - description: bench 同时给出真·朴素 ijk 与 ikj 两个参考，「≥8× vs 朴素 ijk」为验收门槛，ikj 作为性能上限参考展示
    id: both-baselines
    impact: 验收明确且信息完整，bench 输出更诚实
    label: 双基线都要
  - description: 按 assumption 继续
    id: assume-ok
    label: 确认当前假设
  - id: other
    label: 其他（请说明）
  proposed_at: '2026-11-14T07:24:55.752568+00:00'
  question: GEMM 性能验收基线应如何定义？当前 bench 的「naive-ikj」实测已达单核硬件峰值，8× 不可达。
  recommendation:
    id: both-baselines
    reason: 双基线信息最完整：验收门槛用真·朴素 ijk（当前已 30.6×，可达），ikj 留作性能上限参照，避免「基线已达峰值」的误导
  repeat_warning: null
  resolution: both-baselines
  resolved_at: '2026-11-14T07:26:23.975623+00:00'
  topic_normalized: 性能验收基线口径
  uncertainty: R3 写「相对 naive ikj ≥8×」，但 bench 里的 naive-ikj 实测 23.64 GFLOPS 已达单核峰值，按此口径
    8×=189 GFLOPS 超出纯 C 可达范围；需求作者本意可能是经典朴素 ijk（3.56 GFLOPS）而非向量化的 ikj。
- assumption: 当前 R1/R6 约束为「手写实现、依赖编译器自动向量化、不写 intrinsic、无第三方运行时依赖」，AMX 仅通过 bench 里的
    Accelerate 作为上界参照。若要在代码里使能 AMX，就等于修改这条技术选型约束。
  blocking: true
  context: 事实：M1–M4 均有 undocumented AMX 矩阵协处理器，纯 NEON 单核峰值实测 38.5 GFLOPS，Accelerate
    借 AMX 达 1597 GFLOPS。用户代码访问 AMX 有两条路：官方 Accelerate（间接、稳定）或逆向内联汇编（corsix/amx，直接、未文档化、平台锁定、与
    Accelerate 混用有状态冲突风险）。当前双基线验收已可通过（vs 朴素 ijk 8T=30.6×、1T=7.2×）。
  corrected: true
  descent: 3
  description: 是否要在 GEMM 实现里使能 AMX？如要，走官方 Accelerate 还是手写逆向内联汇编？
  deviation: 若不改约束：交付保持纯 C 可移植实现，AMX 只出现在参照行，验收按已裁定的双基线。若改约束：需明确 AMX 是「可选加速后端」还是「交付主体」，并重新定义
    R6 可移植性与 R1 手写实现的范围。
  feedback: 选择手写 AMX 内联汇编后端（实验性，编译开关控制，默认纯 C）；实测不通过则如实标注失败并回退
  id: cfm-20261114-072925-004
  item_type: clarification
  layer: L1-需求拆解
  options:
  - description: R1/R6 不变，AMX 仅作参照行。验收按已裁定的双基线
    id: pure-c-only
    impact: 最快收尾；交付可移植、可审计；性能上限停在 ~109 GFLOPS（8T）
    label: 保持纯 C，拒绝 AMX
  - description: 新增 USE_ACCELERATE 开关，开启时 gemm_f32 走 cblas_sgemm（间接用上 AMX）；默认仍是纯 C
    id: accel-backend
    impact: 工作量小（~1 小时）、稳定拿到 AMX 性能；但该路径不算"我们的内核"，需在验收里单列
    label: 可选 Accelerate 后端（编译开关）
  - description: 按 corsix/amx 的编码直接驱动 AMX（ldx/stx/fma），编译开关控制，默认纯 C
    id: amx-asm
    impact: 技术最具证明力（真·自研 AMX 内核）；但未文档化、平台锁定 M1–M3、与 Accelerate 同进程有状态风险，需实测验证并标注为实验性
    label: 手写 AMX 内联汇编后端
  - description: 默认纯 C，两个可选后端都做，bench 四方对比（纯 C / AMX-asm / Accelerate / 朴素基线）
    id: both-optional
    impact: 最完整的技术验证案例，但工作量最大（估计 3-4 小时），且 AMX-asm 的稳定性风险仍需实测确认
    label: 双后端：Accelerate + 手写 AMX 均作可选
  - description: 按 assumption 继续
    id: assume-ok
    label: 确认当前假设
  - id: other
    label: 其他（请说明）
  proposed_at: '2026-11-14T07:29:25.390387+00:00'
  question: 是否要在 GEMM 实现里使能 AMX？如要，走官方 Accelerate 还是手写逆向内联汇编？
  recommendation:
    id: amx-asm
    reason: 若目标是技术验证与上限突破，手写 AMX 后端最能证明「我们真的驱动了矩阵单元」；Accelerate 后端几乎等于调库，验证价值低。建议
      amx-asm 作实验性可选后端、默认纯 C，实测不通过就如实标注失败并回退
  repeat_warning: null
  resolution: amx-asm
  resolved_at: '2026-11-14T07:30:02.721175+00:00'
  topic_normalized: AMX 技术选型
  uncertainty: AMX 未文档化：raw word 编码依赖逆向资料、不同 macOS/芯片可能失效、与 Accelerate 混用有 AMX 状态冲突风险、违背
    R6 可移植约束；而官方 Accelerate 路径稳定但不属于自研内核。两种价值取向（技术证明 vs 工程稳妥）需要用户定夺。
se_version: '2.0'
---