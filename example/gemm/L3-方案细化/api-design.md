---
se_version: "2.0"
layer: "L3-方案细化"
doc_type: "api-design"
created_at: "2026-11-14T01:47:00+08:00"
---

# 接口设计

## 公共头文件 `include/gemm.h`

```c
#ifndef GEMM_H
#define GEMM_H

#include <stddef.h>

typedef enum {
    GEMM_OK = 0,
    GEMM_EINVAL = 1,
    GEMM_ENOMEM = 2
} gemm_status;

/* C[M,N] = A[M,K] * B[K,N]，全部行主序 float32，C 由调用方预分配 */
gemm_status gemm_f32(int M, int N, int K,
                     const float *A, const float *B, float *C);

/* 参考实现（朴素 ikj），用于正确性对照 */
void gemm_f32_ref(int M, int N, int K,
                  const float *A, const float *B, float *C);

/* 简化路径（小矩阵，无打包） */
void gemm_f32_small(int M, int N, int K,
                    const float *A, const float *B, float *C);

/* 编译期可查询信息 */
const char *gemm_impl_name(void);   /* "vinw-gemm/1.0 (blocked+omp)" */
int gemm_mr(void);                  /* 4 */
int gemm_nr(void);                  /* 8 */

#endif
```

## 内部接口

| 函数 | 签名 | 说明 |
|------|------|------|
| `pack_a` | `void pack_a(int MC,int KC,const float*A,int lda,float*Ap)` | 零填充到 MR 边界 |
| `pack_b` | `void pack_b(int KC,int NC,const float*B,int ldb,float*Bp)` | 零填充到 NR 边界 |
| `macro_kernel` | `void macro_kernel(int KC,const float*Ap,const float*Bp,float*C,int ldc)` | 4×8×KC，C 累加器在寄存器 |
| `gemm_blocked_1t` | `void gemm_blocked_1t(int M,int N,int K,const float*A,const float*B,float*C)` | 单线程全流程 |
| `gemm_blocked_par` | 同上，pthreads 并行（`USE_OPENMP` 时切 omp） | 主入口 `gemm_f32` 调用它 |
| `parallel_for_m` | `void parallel_for_m(int T, ...)` | 按核心权重分配（nblocks>nt 时加权；否则等分）；保底每线程 1 块，无线程池复用（每次调用创建/回收） |

## 构建产物

| 目标 | 产物 | 说明 |
|------|------|------|
| `make` | `build/libgemm.a` | 静态库（`USE_AMX=1` 时为 `build-amx/libgemm.a`） |
| `make test` | `build/test_gemm` | 正确性测试 |
| `make USE_AMX=1 test` | `build-amx/test_gemm` | 含 AMX 用例（591 例） |
| `make bench` | `build/bench_gemm` | 性能基准（链接 Accelerate 作对照） |
| `make clean` | — | 清理 `build/`、`build-amx/`、`lib/` |

两种模式使用**独立构建目录**，避免 `.o` 互相复用（曾因时间戳隔离失效导致假通过）。

## 测试接口约定

- 随机矩阵：`srand(42)` 固定种子，元素 `[-1,1)` 均匀分布
- 容差：`|got - ref| <= 1e-3 * max(1, |ref|)`
- 尺寸集：`{1, 2, 3, 7, 8, 16, 33, 64, 127, 128, 256}` 组合（含 M/N/K 不等、非 MR/NR 整倍数）


## AMX 后端设计（descent-3，实验性）

### 契约

| 项 | 定义 |
|----|------|
| 编译开关 | `make USE_AMX=1`（定义 `-DUSE_AMX=1`），仅 arm64 macOS 生效 |
| 可用性探测 | `gemm_amx_available()`，未编译/非 arm64 返回 0 |
| 未编译行为 | 符号存在，`gemm_amx()` 返回 `GEMM_EINVAL`，调用方回退 `gemm_f32` |
| AMX 状态 ABI | 每 tile 内 `AMX_SET`/`AMX_CLR` 成对，函数返回前必定 `CLR`（AMX 非重入，调用方不得在已启用状态下再调用本后端） |
| 并发 | AMX 状态按线程保存/恢复；多线程各自 `SET`/`CLR` 安全 |

### 数据布局

- tile = 64(M) × 16(N)：`fma32` 四相位 `z_row=t`，每相位 16 行；`Z[j*4+t][i] += x[i]*y[j]`
- **B 打包**：`[n_tile][k][16]`，每 k 行 64B 连续 → pair load 的 128B 恰好覆盖相邻两个 k 步
- **A 打包**：`[k][64]`，每 k 行 256B（4 相位 × 16 行）
- **尾部哨兵**：奇数 k 尾的 pair load 会多读一行，故 B 打包多分配一行并清零（防越界）
- 边角（M % 64 / N % 16）用朴素 ikj 补算，正确性优先

### 已知限制

- AMX 无官方文档（编码出处：corsix/amx）；Apple 不支持、不保证跨 macOS/芯片版本一致
- 平台锁定 M1–M4；M4 另有 SME（本实现未用）
- 与 Accelerate 在同一线程混用需隔离（两者都占用 AMX 状态）
- 单寄存器 `ldx/ldy` 与 pair load 均可工作；本实现选 pair 以减少指令数
