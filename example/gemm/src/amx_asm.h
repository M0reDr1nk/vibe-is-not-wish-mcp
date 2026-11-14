/* Apple AMX 指令封装（最小子集）
 *
 * 来源与致谢：指令编码来自 https://github.com/corsix/amx（Peter Cawley 的逆向工程，
 * 无官方文档、无 Apple 支持）。此处只保留本工程用到的 set/clr/ldx/ldy/stz/fma32。
 *
 * 关键实测结论（M3, macOS 当前版本）：
 *   单寄存器 ldx/ldy（bit62=0）不会把数据送入 fma32 可读的偏移范围，
 *   必须使用 pair load（bit62=1，128 字节 → 两个连续寄存器）。
 */
#ifndef VINW_AMX_ASM_H
#define VINW_AMX_ASM_H

#include <stdint.h>

#define AMX_NOP_OP_IMM5(op, imm5) \
    __asm__ __volatile__("nop\nnop\nnop\n.word (0x201000 + (%0 << 5) + %1)" \
                         : : "i"(op), "i"(imm5) : "memory", "cc")
#define AMX_OP_GPR(op, gpr) \
    __asm__ __volatile__(".word (0x201000 + (%0 << 5) + 0%1 - ((0%1 >> 4) * 6))" \
                         : : "i"(op), "r"((uint64_t)(gpr)) : "memory", "cc")

#define AMX_LDX(g)   AMX_OP_GPR( 0, g)
#define AMX_LDY(g)   AMX_OP_GPR( 1, g)
#define AMX_STZ(g)   AMX_OP_GPR( 5, g)
#define AMX_FMA32(g) AMX_OP_GPR(12, g)
#define AMX_SET()    AMX_NOP_OP_IMM5(17, 0)
#define AMX_CLR()    AMX_NOP_OP_IMM5(17, 1)

/* fma32 矩阵模式操作数：z[j*4 + (row&3)][i] += x[i] * y[j]，f32，全部通道使能。
 * row   : Z 行相位 0..3（每个相位覆盖 16 行）
 * xoff  : x 循环缓冲区字节偏移（0..448，64 的倍数）
 * yoff  : y 循环缓冲区字节偏移
 */
#define AMX_FMA32_OP(row, xoff, yoff) \
    ((uint64_t)(((row) & 3) << 20) | ((uint64_t)(xoff) << 10) | (uint64_t)(yoff))

/* pair load：128 字节 → 连续两个 X/Y 寄存器（bit62=1 由 row+64 置位） */
#define AMX_PAIR_LD_OP(reg, ptr) \
    ((uint64_t)((uint64_t)((reg) + 64) << 56) | (uint64_t)(uintptr_t)(ptr))
/* 单寄存器 Z 行存出：64 字节 ← Z[row] */
#define AMX_STZ_OP(row, ptr) \
    ((uint64_t)((uint64_t)(row) << 56) | (uint64_t)(uintptr_t)(ptr))

#endif /* VINW_AMX_ASM_H */
