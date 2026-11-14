/* AMX GEMM 后端（实验性，USE_AMX 编译开关控制）
 *
 * 设计见 L3 v003：tile = 64(M) x 16(N)，fma32 四相位累积。
 * 打包：B 全局一次 → Bp[K][n_full]（k 主序、n 连续）；A 按 m 块一次 → Ap[K][64]。
 *
 * 实测约束（M3, macOS）：
 *   1) 必须用 pair load（128B→两寄存器）；单寄存器 ldx/ldy 的数据不进 fma32 读取范围
 *   2) 本文件必须 -O2 编译：-O3 的优化与内联汇编寄存器假设冲突，实测 SIGSEGV
 *   3) AMX 无官方文档；失败/不可用时由调用方回退纯 C 路径
 */
#include "gemm.h"

#if defined(USE_AMX) && defined(__aarch64__) && defined(__APPLE__)

#include <stdlib.h>
#include <string.h>

#include "amx_asm.h"

#define AMX_MR 64   /* 4 相位 × 16 行 */
#define AMX_NR 16
#define AMX_KL 8    /* 每批 k 步数（x 缓冲区 8 个 64B 槽） */

int gemm_amx_available(void) { return 1; }
const char *gemm_amx_name(void) { return "vinw-gemm/amx (64x16 tile, fma32)"; }

/* 单个 64×16 输出块（M、N 边界由调用方保证整块） */
static void amx_tile(int K, const float *Ap, const float *Bp, int bstride,
                     float *C, int ldc, int m0, int n0) {
    AMX_SET();
    for (int kb = 0; kb < K; kb += AMX_KL) {
        const int kc = (K - kb < AMX_KL) ? (K - kb) : AMX_KL;
        /* x：kc 个 k 步的 B 行（每步 16 n = 64B），pair load 成对送入 */
        for (int kk = 0; kk + 1 < kc; kk += 2) {
            const float *src = Bp + (size_t)(kb + kk) * bstride;
            AMX_LDX(AMX_PAIR_LD_OP(kk, src));
        }
        if (kc & 1) {  /* 奇数尾：单独一寄存器也走 pair 语义（读入下一行无用数据） */
            const float *src = Bp + (size_t)(kb + kc - 1) * bstride;
            AMX_LDX(AMX_PAIR_LD_OP(kc - 1, src));
        }
        for (int kk = 0; kk < kc; ++kk) {
            const float *ay = Ap + (size_t)(kb + kk) * AMX_MR;
            /* y：4 相位 = 64 行 A，两两 pair load */
            AMX_LDY(AMX_PAIR_LD_OP(0, ay + 0));
            AMX_LDY(AMX_PAIR_LD_OP(2, ay + 32));
            for (int t = 0; t < 4; ++t) {
                AMX_FMA32(AMX_FMA32_OP(t, kk * 64, t * 64));
            }
        }
    }
    /* 取回：相位 t 的第 j 行 → C[m0 + t*16 + j][n0..n0+15] */
    for (int t = 0; t < 4; ++t) {
        for (int j = 0; j < 16; ++j) {
            float *crow = C + (size_t)(m0 + t * 16 + j) * ldc + n0;
            AMX_STZ(AMX_STZ_OP(j * 4 + t, crow));
        }
    }
    AMX_CLR();
}

gemm_status gemm_amx(int M, int N, int K, const float *A, const float *B, float *C) {
    if (M <= 0 || N <= 0 || K <= 0) return GEMM_OK;
    if (!A || !B || !C) return GEMM_EINVAL;

    const int m_full = (M / AMX_MR) * AMX_MR;
    const int n_full = (N / AMX_NR) * AMX_NR;
    if (m_full == 0 || n_full == 0) {
        gemm_f32_small(M, N, K, A, B, C);
        return GEMM_OK;
    }

    float *Bp = (float *)malloc((size_t)K * (size_t)n_full * sizeof(float));
    float *Ap = (float *)malloc((size_t)K * AMX_MR * sizeof(float));
    if (!Bp || !Ap) {
        free(Bp); free(Ap);
        return GEMM_ENOMEM;
    }

    /* B 打包一次：块状布局 [n_tile][k][16]，使每 k 行仅 64B，
     * pair load 的 128B 正好覆盖相邻两个 k 步（这是 fma32 x 偏移的前提） */
    const int ntiles = n_full / AMX_NR;
    for (int t = 0; t < ntiles; ++t) {
        for (int k = 0; k < K; ++k) {
            const float *brow = B + (size_t)k * N + t * AMX_NR;
            float *dst = Bp + ((size_t)t * K + (size_t)k) * AMX_NR;
            memcpy(dst, brow, (size_t)AMX_NR * sizeof(float));
        }
    }

    for (int m0 = 0; m0 < m_full; m0 += AMX_MR) {
        for (int k = 0; k < K; ++k) {
            float *dst = Ap + (size_t)k * AMX_MR;
            for (int m = 0; m < AMX_MR; ++m) {
                dst[m] = A[(size_t)(m0 + m) * K + k];
            }
        }
        for (int n0 = 0, t = 0; n0 < n_full; n0 += AMX_NR, ++t) {
            amx_tile(K, Ap, Bp + (size_t)t * K * AMX_NR, AMX_NR, C, N, m0, n0);
        }
    }

    /* 边角补算（正确性优先，性能次要） */
    for (int m = m_full; m < M; ++m) {
        float *crow = C + (size_t)m * N;
        for (int k = 0; k < K; ++k) {
            const float a = A[(size_t)m * K + k];
            const float *brow = B + (size_t)k * N;
            for (int n = 0; n < N; ++n) crow[n] += a * brow[n];
        }
    }
    if (n_full < N) {
        for (int m = 0; m < m_full; ++m) {
            float *crow = C + (size_t)m * N;
            for (int k = 0; k < K; ++k) {
                const float a = A[(size_t)m * K + k];
                const float *brow = B + (size_t)k * N;
                for (int n = n_full; n < N; ++n) crow[n] += a * brow[n];
            }
        }
    }

    free(Ap); free(Bp);
    return GEMM_OK;
}

#else /* 未启用 AMX */

int gemm_amx_available(void) { return 0; }
const char *gemm_amx_name(void) { return "vinw-gemm/amx (未编译)"; }
gemm_status gemm_amx(int M, int N, int K, const float *A, const float *B, float *C) {
    (void)M; (void)N; (void)K; (void)A; (void)B; (void)C;
    return GEMM_EINVAL;
}

#endif
