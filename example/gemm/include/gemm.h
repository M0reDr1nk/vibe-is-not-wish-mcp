/* VINW GEMM — 本机 CPU 加速矩阵乘法（行主序 float32） */
#ifndef VINW_GEMM_H
#define VINW_GEMM_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    GEMM_OK = 0,
    GEMM_EINVAL = 1,
    GEMM_ENOMEM = 2
} gemm_status;

/* C[M,N] = A[M,K] * B[K,N]，C 由调用方预分配并清零 */
gemm_status gemm_f32(int M, int N, int K,
                     const float *A, const float *B, float *C);

/* 真·朴素 ijk 参考（性能验收基线）：内层步长 N，不做任何优化 */
void gemm_f32_naive_ijk(int M, int N, int K,
                        const float *A, const float *B, float *C);

/* 朴素 ikj 参考实现（正确性对照 / 性能上限参照） */
void gemm_f32_ref(int M, int N, int K,
                  const float *A, const float *B, float *C);

/* 小矩阵简化路径（< 256^3，无打包） */
void gemm_f32_small(int M, int N, int K,
                    const float *A, const float *B, float *C);

/* 强制 NEON 路径（bench 对照 / 用户强制） */
gemm_status gemm_f32_neon(int M, int N, int K,
                          const float *A, const float *B, float *C);

/* AMX 后端（实验性，需 USE_AMX 编译开关；返回 0 表示未编译或不可用） */
int gemm_amx_available(void);
const char *gemm_amx_name(void);
gemm_status gemm_amx(int M, int N, int K,
                     const float *A, const float *B, float *C);

const char *gemm_impl_name(void);
int gemm_mr(void);
int gemm_nr(void);

#ifdef __cplusplus
}
#endif

#endif /* VINW_GEMM_H */
