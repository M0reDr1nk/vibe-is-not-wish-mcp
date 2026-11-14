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
| `parallel_for_m` | `void parallel_for_m(int T, ...)` | M 块区间均分，无线程池复用（每次调用创建/回收） |

## 构建产物

| 目标 | 产物 | 说明 |
|------|------|------|
| `make` | `lib/libgemm.a` | 静态库 |
| `make test` | `build/test_gemm` | 正确性测试 |
| `make bench` | `build/bench_gemm` | 性能基准（链接 Accelerate 作对照） |
| `make clean` | — | 清理 build/lib |

## 测试接口约定

- 随机矩阵：`srand(42)` 固定种子，元素 `[-1,1)` 均匀分布
- 容差：`|got - ref| <= 1e-3 * max(1, |ref|)`
- 尺寸集：`{1, 2, 3, 7, 8, 16, 33, 64, 127, 128, 256}` 组合（含 M/N/K 不等、非 MR/NR 整倍数）
