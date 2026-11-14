/* GEMM：三层分块 + A/B 打包 + 4x8 微内核 + OpenMP 按 M 并行
 * 设计见 L3-方案细化/design-doc.md（asc 前的 v001 基线） */
#include "gemm.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pthread.h>
#include <unistd.h>

#if defined(USE_OPENMP) && defined(_OPENMP)
#include <omp.h>
#define GEMM_HAS_OMP 1
#else
#define GEMM_HAS_OMP 0
#endif

#define MR 4
#define NR 8

#define MC_BLK 128
#define KC_BLK 256
#define NC_BLK 2048

/* 小于该工作量（M*N*K）时走无打包简化路径 */
#define SMALL_THRESHOLD 16777216.0 /* 256^3 */

const char *gemm_impl_name(void) { return "vinw-gemm/1.0 (blocked+omp)"; }
int gemm_mr(void) { return MR; }
int gemm_nr(void) { return NR; }

/* 线程数：GEMM_THREADS 环境变量 > 系统 CPU 数；上限 32 */
static int num_threads(void) {
    const char *env = getenv("GEMM_THREADS");
    int n = 0;
    if (env && *env) {
        n = atoi(env);
    }
    if (n <= 0) {
        long cpus = sysconf(_SC_NPROCESSORS_ONLN);
        n = (cpus > 0) ? (int)cpus : 1;
    }
    if (n > 32) n = 32;
    return n;
}

/* A[mc,kc] (lda) -> Ap[mc_pad][kc][MR]，越界零填充 */
static void pack_a(int mc, int kc, const float *A, int lda, float *Ap) {
    const int mp = (mc + MR - 1) / MR;
    for (int i = 0; i < mp; ++i) {
        for (int p = 0; p < kc; ++p) {
            float *dst = Ap + ((size_t)i * kc + p) * MR;
            for (int r = 0; r < MR; ++r) {
                const int row = i * MR + r;
                dst[r] = (row < mc) ? A[(size_t)row * lda + p] : 0.0f;
            }
        }
    }
}

/* B[kc,nc] (ldb) -> Bp[kc][nc_pad][NR]，越界零填充 */
static void pack_b(int kc, int nc, const float *B, int ldb, float *Bp) {
    const int np = (nc + NR - 1) / NR;
    for (int p = 0; p < kc; ++p) {
        const float *brow = B + (size_t)p * ldb;
        for (int j = 0; j < np; ++j) {
            float *dst = Bp + ((size_t)p * np + j) * NR;
            for (int c = 0; c < NR; ++c) {
                const int col = j * NR + c;
                dst[c] = (col < nc) ? brow[col] : 0.0f;
            }
        }
    }
}

/* 4x8xkc 微内核：acc[4][8] 常驻寄存器；内层按 j 向量化（8 f32 = 2×NEON） */
static void macro_kernel(int mc, int nc, int kc,
                         const float *Ap, const float *Bp,
                         float *C, int ldc) {
    const int mp = (mc + MR - 1) / MR;
    const int np = (nc + NR - 1) / NR;

    for (int i = 0; i < mp; ++i) {
        const int rows = (mc - i * MR < MR) ? (mc - i * MR) : MR;
        for (int j = 0; j < np; ++j) {
            const int cols = (nc - j * NR < NR) ? (nc - j * NR) : NR;

            float acc[MR][NR];
            for (int r = 0; r < MR; ++r)
                for (int c = 0; c < NR; ++c) acc[r][c] = 0.0f;

            for (int p = 0; p < kc; ++p) {
                const float *a = Ap + ((size_t)i * kc + p) * MR;
                const float *b = Bp + ((size_t)p * np + j) * NR;
                /* NR 为编译期常量 → clang 可整段向量化 */
                for (int c = 0; c < NR; ++c) {
                    const float bv = b[c];
                    acc[0][c] += a[0] * bv;
                    acc[1][c] += a[1] * bv;
                    acc[2][c] += a[2] * bv;
                    acc[3][c] += a[3] * bv;
                }
            }

            for (int r = 0; r < rows; ++r) {
                float *crow = C + (size_t)(i * MR + r) * ldc + j * NR;
                for (int c = 0; c < cols; ++c) crow[c] += acc[r][c];
            }
        }
    }
}

/* 小矩阵路径由 gemm_ref.c 提供（无打包 ikj） */

/* pthreads 工作体：处理 ic 块的索引区间 [lo, hi) */
typedef struct {
    int M, N, K;
    int jc, nc, pc, kc;
    int lo, hi;              /* ic 块索引区间 */
    const float *A;
    const float *B;
    float *C;
    float *ap;
    const float *bp;
    int lda, ldb, ldc;
} m_worker_arg;

static void *m_worker(void *raw) {
    m_worker_arg *w = (m_worker_arg *)raw;
    (void)w->N;
    for (int b = w->lo; b < w->hi; ++b) {
        const int ic = b * MC_BLK;
        const int mc = (w->M - ic < MC_BLK) ? (w->M - ic) : MC_BLK;
        pack_a(mc, w->kc, w->A + (size_t)ic * w->lda + w->pc, w->lda, w->ap);
        macro_kernel(mc, w->nc, w->kc, w->ap, w->bp,
                     w->C + (size_t)ic * w->ldc + w->jc, w->ldc);
        (void)w->K;
    }
    return NULL;
}

/* 供 gemm_blocked_par 使用的区间划分（设计文档中的 parallel_for_m 契约） */
static void parallel_for_m(int nblocks, int nt, int worker,
                           int *lo, int *hi) {
    *lo = (worker * nblocks) / nt;
    *hi = ((worker + 1) * nblocks) / nt;
}

/* 按 M 的 ic 块区间并行；T=1 时退化为单线程（gemm_blocked_1t） */
static gemm_status gemm_blocked_par(int M, int N, int K,
                                   const float *A, const float *B, float *C) {
    int nt = num_threads();
    const int nblocks = (M + MC_BLK - 1) / MC_BLK;
    if (nt > nblocks) nt = nblocks;
    if (nt < 1) nt = 1;

    const size_t ap_stride = (size_t)MC_BLK * KC_BLK;
    const size_t bp_size = (size_t)KC_BLK * NC_BLK;

    float *ap_pool = (float *)malloc(ap_stride * (size_t)nt * sizeof(float));
    float *bp = (float *)malloc(bp_size * sizeof(float));
    pthread_t *tids = (pthread_t *)malloc(sizeof(pthread_t) * (size_t)nt);
    m_worker_arg *args = (m_worker_arg *)malloc(sizeof(m_worker_arg) * (size_t)nt);
    if (!ap_pool || !bp || !tids || !args) {
        free(ap_pool); free(bp); free(tids); free(args);
        return GEMM_ENOMEM;
    }
    memset(bp, 0, bp_size * sizeof(float));

    for (int jc = 0; jc < N; jc += NC_BLK) {
        const int nc = (N - jc < NC_BLK) ? (N - jc) : NC_BLK;

        for (int pc = 0; pc < K; pc += KC_BLK) {
            const int kc = (K - pc < KC_BLK) ? (K - pc) : KC_BLK;

            /* B 面板在并行区外打包（共享只读） */
            pack_b(kc, nc, B + (size_t)pc * N + jc, N, bp);

#if GEMM_HAS_OMP
#pragma omp parallel for schedule(static) num_threads(nt)
            for (int t = 0; t < nt; ++t) {
                int lo, hi;
                parallel_for_m(nblocks, nt, t, &lo, &hi);
                m_worker_arg w = {M, N, K, jc, nc, pc, kc, lo, hi,
                                  A, B, C, ap_pool + (size_t)t * ap_stride, bp, K, N, N};
                m_worker(&w);
            }
            (void)tids; (void)args;
#else
            for (int t = 0; t < nt; ++t) {
                int lo, hi;
                parallel_for_m(nblocks, nt, t, &lo, &hi);
                args[t] = (m_worker_arg){M, N, K, jc, nc, pc, kc, lo, hi,
                                         A, B, C, ap_pool + (size_t)t * ap_stride, bp, K, N, N};
            }
            int started = 0;
            for (int t = 0; t < nt; ++t) {
                if (args[t].lo >= args[t].hi) continue;
                if (pthread_create(&tids[started], NULL, m_worker, &args[t]) != 0) {
                    /* 线程创建失败：该线程区间由本线程兜底执行 */
                    m_worker(&args[t]);
                    continue;
                }
                ++started;
            }
            for (int t = 0; t < started; ++t) pthread_join(tids[t], NULL);
#endif
        }
    }

    free(ap_pool);
    free(bp);
    free(tids);
    free(args);
    return GEMM_OK;
}

/* 单线程版本：与并行版共用同一路径，避免两条实现漂移 */
static gemm_status gemm_blocked_1t(int M, int N, int K,
                                   const float *A, const float *B, float *C) {
    const char *saved = getenv("GEMM_THREADS");
    char saved_buf[32];
    saved_buf[0] = '\0';
    if (saved) { snprintf(saved_buf, sizeof(saved_buf), "%s", saved); }
    setenv("GEMM_THREADS", "1", 1);
    gemm_status st = gemm_blocked_par(M, N, K, A, B, C);
    if (saved_buf[0]) setenv("GEMM_THREADS", saved_buf, 1);
    else unsetenv("GEMM_THREADS");
    return st;
}

gemm_status gemm_f32(int M, int N, int K, const float *A, const float *B, float *C) {
    if (M <= 0 || N <= 0 || K <= 0) return GEMM_OK; /* 幂等空操作 */
    if (!A || !B || !C) return GEMM_EINVAL;

    if ((double)M * (double)N * (double)K < SMALL_THRESHOLD) {
        gemm_f32_small(M, N, K, A, B, C);
        return GEMM_OK;
    }
    if (num_threads() <= 1) return gemm_blocked_1t(M, N, K, A, B, C);
    return gemm_blocked_par(M, N, K, A, B, C);
}
