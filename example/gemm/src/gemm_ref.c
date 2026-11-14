#include "gemm.h"

#include <stddef.h>

/* 朴素 ikj：C 按行遍历，B 行主序顺序访问 */
void gemm_f32_ref(int M, int N, int K, const float *A, const float *B, float *C) {
    for (int i = 0; i < M; ++i) {
        for (int k = 0; k < K; ++k) {
            const float a = A[(size_t)i * K + k];
            const float *brow = B + (size_t)k * N;
            float *crow = C + (size_t)i * N;
            for (int j = 0; j < N; ++j) {
                crow[j] += a * brow[j];
            }
        }
    }
}

/* 真·朴素 ijk：内层对 k 求和，步长 N —— 经典朴素序，作为验收基线 */
void gemm_f32_naive_ijk(int M, int N, int K, const float *A, const float *B, float *C) {
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N; ++j) {
            float s = 0.0f;
            for (int k = 0; k < K; ++k) {
                s += A[(size_t)i * K + k] * B[(size_t)k * N + j];
            }
            C[(size_t)i * N + j] = s;
        }
    }
}

void gemm_f32_small(int M, int N, int K, const float *A, const float *B, float *C) {
    gemm_f32_ref(M, N, K, A, B, C);
}
