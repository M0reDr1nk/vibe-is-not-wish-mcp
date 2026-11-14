/* AMX GEMM 后端（实验性，USE_AMX 编译开关控制）
 *
 * 设计见 L3 v003：tile = 64(M) x 16(N)，fma32 四相位累积。
 * 打包：B 全局一次 → Bp[K][n_full]（k 主序、n 连续）；A 按 m 块一次 → Ap[K][64]。
 *
 * 实测要点（M3, macOS）：
 *   1) 单寄存器 ldx/ldy 与 pair load 均可用；本实现选 pair load 以减少指令数，
 *      代价是奇数 k 尾会多读一行，故 Bp 额外保留一行零填充（防越界）
 *   2) AMX 无官方文档（编码见 amx_asm.h 出处）；未编译/不可用时调用方回退纯 C 路径
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

    /* 多分配一行并清零：奇数 k 尾的 pair load 会读入相邻两行 128B，
     * 最后一行没有"下一行"，因此额外保留一行零填充（见 L3 AMX 设计） */
    const size_t bp_rows = (size_t)K + 1;
    float *Bp = (float *)malloc(bp_rows * (size_t)n_full * sizeof(float));
    float *Ap = (float *)malloc((size_t)K * AMX_MR * sizeof(float));
    if (!Bp || !Ap) {
        free(Bp); free(Ap);
        return GEMM_ENOMEM;
    }

    /* B 打包一次：块状布局 [n_tile][k][16]，使每 k 行仅 64B，
     * pair load 的 128B 正好覆盖相邻两个 k 步 */
    const int ntiles = n_full / AMX_NR;
    const size_t tile_stride = (size_t)(K + 1) * AMX_NR;
    for (int t = 0; t < ntiles; ++t) {
        for (int k = 0; k < K; ++k) {
            const float *brow = B + (size_t)k * N + t * AMX_NR;
            float *dst = Bp + (size_t)t * tile_stride + (size_t)k * AMX_NR;
            memcpy(dst, brow, (size_t)AMX_NR * sizeof(float));
        }
        /* 尾部哨兵行清零 */
        memset(Bp + (size_t)t * tile_stride + (size_t)K * AMX_NR, 0,
               (size_t)AMX_NR * sizeof(float));
    }

    for (int m0 = 0; m0 < m_full; m0 += AMX_MR) {
        for (int k = 0; k < K; ++k) {
            float *dst = Ap + (size_t)k * AMX_MR;
            for (int m = 0; m < AMX_MR; ++m) {
                dst[m] = A[(size_t)(m0 + m) * K + k];
            }
        }
        for (int n0 = 0, t = 0; n0 < n_full; n0 += AMX_NR, ++t) {
            amx_tile(K, Ap, Bp + (size_t)t * tile_stride, AMX_NR, C, N, m0, n0);
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
