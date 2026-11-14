/* 性能基准：naive / blocked-1T / blocked-MT / Accelerate 对比 */
#include "gemm.h"

#define ACCELERATE_NEW_LAPACK
#include <Accelerate/Accelerate.h>
#include <math.h>
#include <string.h>

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static void set_threads(int n) {
    char buf[16];
    snprintf(buf, sizeof(buf), "%d", n);
    setenv("GEMM_THREADS", buf, 1);
}

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static void fill(float *p, size_t n) {
    for (size_t i = 0; i < n; ++i) p[i] = (float)rand() / (float)RAND_MAX - 0.5f;
}

static void vinw_gemm_bench(int M, int N, int K,
                            const float *A, const float *B, float *C) {
    (void)gemm_f32(M, N, K, A, B, C);
}

static double run_once(int M, int N, int K, const float *A, const float *B, float *C,
                       void (*fn)(int, int, int, const float *, const float *, float *)) {
    for (size_t i = 0; i < (size_t)M * N; ++i) C[i] = 0.0f;
    const double t0 = now_sec();
    fn(M, N, K, A, B, C);
    return now_sec() - t0;
}

static double gflops(int M, int N, int K, double sec) {
    const double fl = 2.0 * (double)M * (double)N * (double)K;
    return sec > 0 ? fl / sec / 1e9 : 0.0;
}

static void bench_shape(int M, int N, int K, int threads) {
    float *A = malloc((size_t)M * K * sizeof(float));
    float *B = malloc((size_t)K * N * sizeof(float));
    float *C = malloc((size_t)M * N * sizeof(float));
    fill(A, (size_t)M * K);
    fill(B, (size_t)K * N);
    fill(C, (size_t)M * N);

    printf("\n=== %dx%dx%d (threads=%d) ===\n", M, N, K, threads);
    printf("%-22s %10s %12s\n", "impl", "time(ms)", "GFLOPS");

    struct { const char *name; void (*fn)(int, int, int, const float *, const float *, float *); } impls[] = {
        {"naive-ikj", gemm_f32_ref},
        {"vinw-blocked", vinw_gemm_bench},
    };

    for (int i = 0; i < 2; ++i) {
        setenv("GEMM_THREADS", (char[]){0}, 0);
        run_once(M, N, K, A, B, C, impls[i].fn); /* 预热 */
        double best = 1e9;
        int reps = (M <= 256) ? 20 : 5;
        for (int r = 0; r < reps; ++r) {
            double t = run_once(M, N, K, A, B, C, impls[i].fn);
            if (t < best) best = t;
        }
        printf("%-22s %10.3f %12.2f\n", impls[i].name, best * 1e3, gflops(M, N, K, best));
    }

    /* Accelerate 上界参考 */
    {
        for (size_t i = 0; i < (size_t)M * N; ++i) C[i] = 0.0f;
        cblas_sgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, M, N, K,
                    1.0f, A, K, B, N, 0.0f, C, N);
        double best = 1e9;
        int reps = (M <= 256) ? 20 : 5;
        for (int r = 0; r < reps; ++r) {
            for (size_t i = 0; i < (size_t)M * N; ++i) C[i] = 0.0f;
            double t0 = now_sec();
            cblas_sgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, M, N, K,
                        1.0f, A, K, B, N, 0.0f, C, N);
            double t = now_sec() - t0;
            if (t < best) best = t;
        }
        printf("%-22s %10.3f %12.2f\n", "accelerate(cblas)", best * 1e3, gflops(M, N, K, best));
    }

    free(A); free(B); free(C);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    srand(42);
    printf("impl: %s\n", gemm_impl_name());
    printf("max threads: %d\n", 1);

    int shapes[][3] = {{256, 256, 256}, {512, 512, 512}, {1024, 1024, 1024}, {2048, 2048, 2048}};
    for (int i = 0; i < 4; ++i) bench_shape(shapes[i][0], shapes[i][1], shapes[i][2], 8);

    printf("\n=== 线程扩展性 (1024^3) ===\n");
    printf("%-8s %12s %10s\n", "threads", "GFLOPS", "speedup");
    double base = 0;
    for (int t = 1; t <= 8; t *= 2) {
        float *A = malloc((size_t)1024 * 1024 * sizeof(float));
        float *B = malloc((size_t)1024 * 1024 * sizeof(float));
        float *C = malloc((size_t)1024 * 1024 * sizeof(float));
        fill(A, 1024 * 1024); fill(B, 1024 * 1024);
        set_threads(t);
        run_once(1024, 1024, 1024, A, B, C, vinw_gemm_bench);
        double best = 1e9;
        for (int r = 0; r < 5; ++r) {
            double tt = run_once(1024, 1024, 1024, A, B, C, vinw_gemm_bench);
            if (tt < best) best = tt;
        }
        double g = gflops(1024, 1024, 1024, best);
        if (t == 1) base = g;
        printf("%-8d %12.2f %10.2fx\n", t, g, base > 0 ? g / base : 1.0);
        free(A); free(B); free(C);
    }
    return 0;
}
