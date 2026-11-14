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
