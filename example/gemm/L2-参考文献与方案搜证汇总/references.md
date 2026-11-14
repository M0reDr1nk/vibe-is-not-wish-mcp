---
se_version: "2.0"
layer: "L2-参考文献与方案搜证汇总"
doc_type: "references"
created_at: "2026-11-14T01:35:00+08:00"
---

# 参考文献与方案搜证 — GEMM CPU 优化

## 经典文献

| 来源 | 核心贡献 | 本项目采用点 |
|------|---------|-------------|
| Goto & van de Geijn (2008), *Anatomy of High-Performance Matrix Multiplication* | 三层分块 (MC/KC/NC) + A/B 打包 + MR×NR 微内核，把 GEMM 变成 L1-resident 的 rank-1 更新 | 整体三层分块骨架 |
| BLIS 论文 (Van Zee & van de Geijn, 2015) | 以微内核为抽象中心，其余层围绕它自动分块；明确"微内核决定峰值" | 微内核优先的设计顺序 |
| OpenBLAS 实现笔记 | 参数自动调优（大小由 CPU 型号决定）、GEBP 打包 | 参数从缓存容量推导而非硬编码 |
| Agner Fog, *Optimizing software in C++* | 缓存行 64B、prefetch、循环顺序对依赖链的影响 | 循环序、packing 布局、避免 store-forwarding 停顿 |
| ARM NEON Programmer's Guide | `vfmaq_f32` 延迟/吞吐、128-bit 向量 = 4×f32 | arm64 微内核 4 元素向量化，累加器数量选 4~8 |

## 现有方案对比

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|---------|
| 朴素 ikj 三重循环 | 实现简单、正确性基准 | 约 1-3 GFLOPS，无法发挥多级缓存 | 采用（作为参考实现与性能基线） |
| 直接调用 Accelerate cblas_sgemm | 极致性能（数十 GFLOPS） | 不是"实现"，只是调用 | **仅作为性能上界参考**，不作为交付实现 |
| 三层分块 + 打包 + 微内核（手写） | 教学与工程价值高；可移植；理解每个 GFLOP 来源 | 参数需手工调 | **采用（主实现）** |
| 依赖编译器自动向量化（`-O3 -ffast-math`） | 零 intrinsic 成本 | 编译器对复杂循环常放弃向量化 | 采用（首选方案） |
| 手写 NEON/AVX intrinsic | 峰值最高 | 平台绑定、维护成本高 | 暂不采用（列为后续优化项） |

## 关键事实（决定设计）

1. **Apple M 系列缓存**：L1D 通常 128KB、L2 12–32MB（P-core 独占）、L3 共享。GEMM 分块需让 `KC×NC` 的 B 面板驻留 L2，`MC×KC` 的 A 面板驻留 L3。
2. **`vfmaq_f32`（FMA）是吞吐关键**：C 累加器在寄存器中不落内存，是 15×+ 加速的主要来源。
3. **行主序（RowMajor）**：C 与 A 按行连续；B 需要打包成列式小块才能让微内核顺序访问。
4. **OpenMP 并行维度选 M**：按 M 分块并行，各线程写各自 C 行块，无写冲突、无锁。
5. **浮点误差**：分块改变累加顺序，误差随 K 增大；相对容差 1e-3 对 1e3 量级 K 足够。
