---
se_version: "2.0"
layer: "L3-方案细化"
doc_type: "design-doc"
created_at: "2026-11-14T01:45:00+08:00"
---

# 设计文档 — GEMM CPU 加速

## 1. 总体结构（Goto/BLIS 五层循环）

```
for jc in 0..N step NC          # ① N 分块（L2 驻留 B 面板）
  pack B[jc:jc+NC, :] -> Bp     # 列主序打包，供微内核顺序读
  for pc in 0..K step KC        # ② K 分块（控制 A 面板体积）
    pack A[:, pc:pc+KC] -> Ap   # 行主序按 MC 分块打包
    for ic in 0..M step MC      # ③ M 分块（L3/L2 驻留 A 面板）
      for jr in 0..NC step NR   # ④ 微内核列块
        for ir in 0..MC step MR # ⑤ 微内核行块
          macro_kernel(MR×NR, KC)   # C 累加器常驻寄存器
```

## 2. 微内核（4×8）

```c
// C[4][8] 累加器常驻 8 个 NEON 寄存器（每寄存器 4×f32）
// 对 p in 0..KC:
//   a0..a3 = Ap[p][0..3]        （4 个标量，广播）
//   bv0, bv1 = Bp[p][0..7]      （2 个 NEON 向量）
//   C[i] += a_i * bv            （8 次 FMA/行，共 32 FMA/迭代）
```

- **MR=4, NR=8**：C 占 8 个向量寄存器，A 广播用标量，B 用 2 个向量 → 寄存器压力 ~14/32，安全
- 内层 `p` 循环展开 4 次，减少循环开销与提高 FMA 密度
- `-O3 -march=native -ffast-math` 让 clang 生成 `fmla` 指令

## 3. 打包布局

| 面板 | 布局 | 理由 |
|------|------|------|
| Ap | `[MC/MR][KC][MR]`，MR 连续 | 微内核内层按 MR 连续读，向量化友好 |
| Bp | `[KC][NC/NR][NR]`，NR 连续 | 微内核取 2 个 128-bit 向量 |

如果 `K % KC != 0` 或 `M % MR != 0`，打包时零填充到边界。

## 4. 并行策略（v002 修订：环境驱动）

> **修订原因**：L3 v001 指定 OpenMP，但实测本机 Apple clang 21 不支持 `-fopenmp`，系统也无 `libomp`。
> 设计目标不变（按 M 行块并行、无归约、无锁），**机制改为 pthreads 主实现，OpenMP 作为可选后端**（`-DUSE_OPENMP` 且运行时存在时启用；`-fopenmp` 但未编译时不引入任何 omp 符号）。

```c
/* 主实现：pthreads 线程池，每个线程负责 M 的一个连续块区间 */
parallel_for_m(num_threads, N, K, A, B, C, jc, pc, ...);
```

实现约定：
- 工作划分：按 `ic` 块的**索引区间**均分给 T 个线程（`blocks_per_thread = ceil(nblocks / T)`），静态调度，无任务队列、无原子量
- 各线程独占一段 C 行块 → 无数据竞争、无需归约
- A 面板缓冲：每线程独占 `MC*KC` 浮点（线程数 × 128KB）
- B 面板：并行区外打包，各线程只读共享
- 线程数：`min(GET_THREADS, nblocks)`，可由环境变量 `GEMM_THREADS` 覆盖
- 编译期：`#ifdef USE_OPENMP` 走 omp 分支（保留给有 libomp 的环境），默认走 pthreads

对应设计目标检查（不变）：
| 目标 | 满足方式 |
|------|---------|
| 按 M 并行 | 线程按 ic 块索引区间划分 |
| 无归约 | K 完整遍历于线程内部，C 行块不跨线程 |
| 可移植 | pthreads 是 POSIX 标准，macOS/Linux 均有 |

## 5. 小矩阵简化路径（M*N*K < 256³）

跳过打包，直接朴素 ikj + 编译器自动向量化，避免打包开销压过收益；bench 中明确标注"非调优区间"。

## 6. 数据流与内存

| 缓冲 | 大小 | 生命周期 |
|------|------|---------|
| Ap | MC×KC×4B = 128KB | 每次 ic 迭代 |
| Bp | KC×NC×4B = 2MB | 每次 jc 迭代 |

## 7. 错误处理

- `M/N/K <= 0` → 直接返回（幂等空操作）
- 空指针且尺寸非零 → 返回错误码（`GEMM_EINVAL`）
- 不抛异常（C ABI）

## 8. 性能预期（arm64, P-core 单线程）

| 实现 | 预期 GFLOPS | 依据 |
|------|------------|------|
| naive ikj | 1–3 | 内存带宽受限 |
| blocked 1T | 15–25 | FMA 吞吐 ~ 60-80% 峰值 |
| blocked MT (8T) | 60–120 | 多核线性扩展 |
| Accelerate | 80–150 | 工业级调优上界 |

> 交付门槛（R3/R4）：相对 naive ≥ 8×（单线程）、8 线程 ≥ 4× 单线程。

---

# descent-3 设计修订（v003）：双基线验收 + 微内核与并行优化

## 1. 双基线验收（承接 L1 修订）

### 接口新增

```c
/* 真·朴素 ijk 参考（验收基线）：内层步长 N，不做任何优化 */
void gemm_f32_naive_ijk(int M, int N, int K, const float *A, const float *B, float *C);
```

### bench 输出契约

每个尺寸段输出四行 + 一行门槛判定：

```
naive-ijk       (验收基线)
naive-ikj       (上限参照)
vinw-blocked
accelerate(cblas)

gate: blocked/naive-ijk = XX.Xx  (门槛 8x: PASS/FAIL, 线程 N)
```

同时输出 `gate-st: blocked-1T/naive-ijk-1T`（单线程门槛判定）。

## 2. 微内核优化（目标：ST 从 25.14 → ≥28.5 GFLOPS）

### 现状瓶颈分析

4×8 微内核每 k 步：8 个向量 FMA（acc[4][8] = 8×v4）+ 2 次 b 装载 + 4 次 a 广播，
但循环体内有 3 处指针运算（`((size_t)i*kc+p)*MR`、`((size_t)p*np+j)*NR`）。

### 方案（按风险从低到高）

| 方案 | 做法 | 预期 | 风险 |
|------|------|------|------|
| A. 指针递增 | 把下标乘法改为指针 += 步长 | +5~10% | 无 |
| B. k 方向 2 路展开 | 一次处理 p 和 p+1，复用 b 装载 | +8~15% | 代码重复 |
| C. 8×8 分块 | acc 16 个 v4（64 float）+ 8 b 向量 → 寄存器压力大 | 未知 | 可能 spill 反而更慢 |

先做 A+B，实测后再决定是否试 C。若仍 <28.5，记录实际值并如实标记门槛 FAIL（不得改门槛）。

## 3. 并行优化（扩展性 4.34× → 目标 5×+）

| 方案 | 做法 | 说明 |
|------|------|------|
| D. 按算力加权分块 | P 核多分块、E 核少分块 | 需探测核心类型（macOS 可用 QoS 或 sysctl perflevel） |
| E. B 面板并行打包 | 把 pack_b 拆进并行区（每线程负责部分 kc 行） | 消除串行段 |

先做 E（简单、对 2048³ 收益明显），D 需平台相关探测，标记可选。

## 4. 验收对应

| R | 验收 | 本轮目标 |
|---|------|---------|
| R2 正确性 | `make test` 586+ 用例通过 | 保持全绿，新增 naive_ijk 与 blocked 的对比用例 |
| R3 ST 性能 | ST ≥ 8× naive-ijk | 28.5 GFLOPS |
| R4 扩展性 | 8T/1T ≥ 4× | 已 4.34×，保持 |
| R5 bench | 双基线 + 门槛判定输出 | bench 改造 |

---

# descent-4 设计修订（v004）：R4 扩展性达标的加权并行

## 问题复现（descent-3 终测）

1024³ 线程扫描：1T=40.5、2T=74.1（1.83×）、4T=99.2（2.45×）、8T=130.5（3.22×），
门槛 R4 = 8T/1T ≥ 4× → **FAIL**。

## 根因

1. **静态等分**：`parallel_for_m` 按块数等分，M3 为 4P+4E（E 核约 P 核一半吞吐），
   E 核线程完成同样工作量需约 2 倍时间 → 成为尾延迟
2. **粒度太粗**：MC=128 时 1024³ 只有 8 个 ic 块，无法按算力细分配

理论上限：总吞吐 ≈ 4×1 + 4×0.5 = 6 单位 → 6×；当前 3.22× 说明有 ~1.9× 可抢。

## 设计

### D1. MC 降至 64（细粒度）

1024³ → 16 个 ic 块；每线程获得 1~3 块，可按权重分配。代价：A 面板重打包次数翻倍
（每块 64×256 float = 64KB），实测可接受。

### D2. 按 perflevel 加权分块

```
P 核权重 2.0；E 核权重 1.0
总权重 W = nP*2 + nE*1
线程 t 分到块数 ∝ weight(t)/W
```

核心类型探测（macOS）：
- `sysctlbyname("hw.perflevel0.logicalcpu")` → P 核数
- `sysctlbyname("hw.perflevel1.logicalcpu")` → E 核数
- 探测失败 → 退化等权（行为与 v003 一致）

线程 t 的核心类型无法直接指定（pthread 无亲和性 API），因此采用
**按权重分配工作量 + 线程序号优先占用 P 核**的策略；即使调度不理想，
加权分配仍能减少尾延迟（E 核线程工作量更少）。

### D3. 分块边界计算

```
cum[t] = round(total_blocks * sum(weight[0..t]) / W)
lo = cum[t-1], hi = cum[t]
```

## 验收

| 门槛 | 定义 | 目标 |
|------|------|------|
| R4 | 8T/1T ≥ 4× | ≥ 4.0× |
| R3 回归 | blocked-1T/naive-ijk-1T ≥ 8× | 不得低于 19× |

若加权后仍 < 4×，如实记录 FAIL 并分析（不得改门槛）。

## 风险

- MC=64 可能降低单线程性能（R3 回归风险）→ 必须同时验证 R3
- 加权分配依赖 perflevel 探测；探测失败时退化为等分（不劣于 v003）
