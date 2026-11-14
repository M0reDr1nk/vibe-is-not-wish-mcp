---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "implementation"
updated_at: "2026-11-13T17:28:57.213413+00:00"
---

# 实现笔记

## 关键代码决策

## 与设计文档的映射

| 设计文档段落 | 代码位置 | 实现状态 |
|-------------|---------|---------|
| — | — | — |

## 待解决问题

- [ ] —

## descent-3 实现记录：双基线 + AMX 后端

### 1. 双基线 bench（L1 裁定 both-baselines）

- `gemm_f32_naive_ijk`：真·朴素 ijk 参考（验收基线）
- bench 输出四实现 + 门槛行：`gate blocked/naive-ijk = XX.XXx (门槛 8x: PASS/FAIL)`
- ikj 与 Accelerate 保留为上限参照

### 2. NEON 微内核优化

- 指针提升 + k 方向 2 路展开
- 实验结果：4×8 / 4×12 / 6×8 / 8×8 四种 tile 形状实测差异 < 2%（25.14 → 25.66 GFLOPS）
- 结论：clang 对 4×8 已充分向量化，形状调优收益有限

### 3. AMX 后端（实验性，`make USE_AMX=1`）

**可行性验证（关键发现）**

| 发现 | 结论 |
|------|------|
| 用户态 AMX 在 M3 + 当前 macOS **可用**（无 SIGILL） | corsix/amx 官方测试套件 10+ 指令全部 OK |
| 单寄存器 `ldx/ldy`（bit62=0）**不进入 fma32 读取范围** | 必须用 pair load（bit62=1，128B→两寄存器） |
| pair load 要求相邻两个 k/相位步**内存连续** | B 必须块状打包 `[n_tile][k][16]` |
| `-O3` 下内联汇编寄存器假设被优化破坏 → 按空指针执行 ldx（SIGSEGV） | 该文件固定 `-O2` 编译 |

**实现**

- tile = 64(M) × 16(N)，fma32 四相位累积（每相位 16 行）
- A 按 m 块打包 `[k][64]`（每 m 块一次）；B 全局一次块状打包 `[n_tile][k][16]`
- 边角块（M 非 64 倍数 / N 非 16 倍数）用朴素 ikj 补算
- 未编译 AMX 时符号存在但返回 `GEMM_EINVAL`，调用方回退

**实测（1024³，单线程 AMX）**

| 实现 | GFLOPS | 相对朴素 ijk |
|------|-------:|------------:|
| naive-ijk | 1.74 | 1× |
| naive-ikj | 17.69 | 10× |
| NEON blocked（8 线程） | 119.25 | 69× |
| **AMX 后端（单线程）** | **866.62** | **499×** |
| Accelerate cblas | 1326 | 762× |

AMX 单线程即达 NEON 8 线程的 7.3 倍、Accelerate 的 65%——验证了「自研 AMX 内核」的技术路径成立。

**诚实披露**：AMX 未文档化、平台锁定（M1–M4）、`-O2` 限制、与 Accelerate 同进程混用需隔离（bench 已分段执行）；生产使用需自行评估风险。
