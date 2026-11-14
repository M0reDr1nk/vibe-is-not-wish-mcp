/* 正确性测试：与朴素参考实现逐元素对比 */
#include "gemm.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static float frand_unit(void) {
    return (float)rand() / (float)RAND_MAX * 2.0f - 1.0f; /* [-1,1) */
}

static int check_case(int M, int N, int K) {
    const size_t asz = (size_t)M * K, bsz = (size_t)K * N, csz = (size_t)M * N;
    float *A = malloc(asz * sizeof(float));
    float *B = malloc(bsz * sizeof(float));
    float *C = calloc(csz, sizeof(float));
    float *R = calloc(csz, sizeof(float));
    if (!A || !B || !C || !R) { printf("  alloc fail\n"); free(A); free(B); free(C); free(R); return 0; }

    for (size_t i = 0; i < asz; ++i) A[i] = frand_unit();
    for (size_t i = 0; i < bsz; ++i) B[i] = frand_unit();

    gemm_f32_ref(M, N, K, A, B, R);
    gemm_status st = gemm_f32(M, N, K, A, B, C);

    int ok = (st == GEMM_OK);
    float maxdiff = 0.0f;
    size_t bad = 0;
    for (size_t i = 0; i < csz; ++i) {
        float diff = fabsf(C[i] - R[i]);
        float tol = 1e-3f * fmaxf(1.0f, fabsf(R[i]));
        if (diff > maxdiff) maxdiff = diff;
        if (diff > tol) ++bad;
    }
    if (bad) ok = 0;
    printf("  %4d x %4d x %4d  %s  maxdiff=%.3e  bad=%zu  status=%d\n",
           M, N, K, ok ? "PASS" : "FAIL", maxdiff, bad, (int)st);

    free(A); free(B); free(C); free(R);
    return ok;
}

int main(void) {
    srand(42);
    printf("gemm impl: %s (MR=%d NR=%d)\n", gemm_impl_name(), gemm_mr(), gemm_nr());

    int sizes[] = {1, 2, 3, 7, 8, 16, 33, 64, 127, 128, 129, 256};
    const int ns = (int)(sizeof(sizes) / sizeof(sizes[0]));
    int total = 0, passed = 0;

    printf("\n[1] 方阵扫描（含 MR/NR 非整倍数与边界）\n");
    for (int i = 0; i < ns; ++i) {
        for (int j = 0; j < ns; ++j) {
            for (int k = 0; k < ns; ++k) {
                /* 抽样：避免 12^3 全组合过慢，保留非方阵与边界组合 */
                if ((i + j + k) % 3 != 0) continue;
                ++total;
                passed += check_case(sizes[i], sizes[j], sizes[k]);
            }
        }
    }

    printf("\n[2] 非方阵与极端形状\n");
    int shapes[][3] = {{1, 256, 1}, {256, 1, 1}, {1, 1, 256}, {3, 1000, 7},
                       {128, 128, 1}, {1, 128, 128}, {517, 3, 11}};
    for (int i = 0; i < 7; ++i) {
        ++total;
        passed += check_case(shapes[i][0], shapes[i][1], shapes[i][2]);
    }

    printf("\n[3] 边界与错误处理\n");
    float dummy = 0.0f;
    int edge_ok = 1;
    if (gemm_f32(0, 4, 4, &dummy, &dummy, &dummy) != GEMM_OK) edge_ok = 0;
    if (gemm_f32(-1, 4, 4, &dummy, &dummy, &dummy) != GEMM_OK) edge_ok = 0;
    if (gemm_f32(4, 4, 4, NULL, &dummy, &dummy) != GEMM_EINVAL) edge_ok = 0;
    printf("  空操作/非法参数: %s\n", edge_ok ? "PASS" : "FAIL");
    ++total; passed += edge_ok;

    printf("\n[4] 大规模路径（触发分块）\n");
    ++total; passed += check_case(300, 300, 300); /* 27M > 阈值 16.7M */
    ++total; passed += check_case(257, 129, 65);  /* 2.1M < 阈值 → 简化路径 */

    printf("\n==== %d/%d 通过 ====\n", passed, total);
    return passed == total ? 0 : 1;
}
