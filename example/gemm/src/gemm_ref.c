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

void gemm_f32_small(int M, int N, int K, const float *A, const float *B, float *C) {
    gemm_f32_ref(M, N, K, A, B, C);
}
