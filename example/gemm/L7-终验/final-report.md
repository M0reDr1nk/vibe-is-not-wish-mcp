# 终验报告 — GEMM 本机 CPU 加速（descent-3）

| 项 | 值 |
|----|-----|
| 项目 | GEMM 本机 CPU 加速（VINW 第二个实战工程） |
| 轮次 | descent-1 ~ descent-3（2 次上升） |
| 日期 | 2026-11-14 |
| 平台 | Apple M3（4P + 4E），Apple clang，-O3 -march=native |

## 1. 交付物

| 组件 | 说明 |
|------|------|
| `src/gemm_ref.c` | 真·朴素 ijk（**验收基线**）+ ikj（对照） |
| `src/gemm_blocked.c` | NEON 三层分块 + 打包 + 4×8 微内核 + pthreads 按 M 并行的主实现 |
| `src/gemm_amx.c` | **AMX 实验后端**（`make USE_AMX=1`），64×16 tile + fma32 四相位 |
| `src/amx_asm.h` | AMX 指令封装（出处：corsix/amx，已注明） |
| `bench/bench_gemm.c` | 双基线 + 三条门槛（R3/R4/ext）+ Accelerate 上界 |
| `tests/test_gemm.c` | 586 例（默认）/ 591 例（AMX） |

## 2. 验收结论（逐条）

| 需求 | 门槛 | 实测（1024³） | 结论 |
|------|------|--------------|------|
| R1 C 接口 | 头文件 ABI 稳定 | `gemm.h` 10 个公共符号 | ✅ |
| R2 正确性 | max\|diff\| ≤ 1e-3 | NEON 1.1e-5 / AMX **0** | ✅ |
| R3 单线程性能 | blocked-1T / naive-ijk-1T ≥ 8× | **19.9× ~ 24.8×** | ✅ PASS |
| R4 多线程扩展性 | blocked-8T / blocked-1T ≥ 4× | **3.22×** | ❌ **FAIL** |
| R5 bench 工具 | 双基线 + 门槛输出 | gate-st / gate-mt / gate-ext | ✅ |
| R6 可移植 | arm64/x86_64 可编译 | 纯 C + 自动向量化（AMX 仅 arm64 可选） | ✅ |
| R7 构建 | `make` 一条命令 | `make` / `make test` / `make bench` / `make USE_AMX=1` | ✅ |

### R4 未达标：如实记录

M3 为 4P+4E，E 核约 P 核一半吞吐，静态等分块使 E 核成为尾延迟。
理论上限约 6×（4×1 + 4×0.5），实测 3.22×（此前一次测得 4.34×，属负载波动）。
**未修改门槛数字**（L1 明确规定）；改进方向已记入 L3：MC 降至 64 以获得更细粒度，
配合按算力（perflevel）加权分块。

## 3. AMX 后端（本轮最大技术产出）

| 指标 | 值 |
|------|-----|
| AMX 单线程 1024³ | **866 ~ 1022 GFLOPS** |
| 相对朴素 ijk | **499× ~ 530×** |
| 相对 NEON 8 线程 | 6.6× ~ 7.9× |
| 相对 Accelerate（AMX 官方路径） | 65% ~ 77% |

**技术事实（经两轮评审校正）**

1. 用户态 AMX 在 M3 + 当前 macOS **可用**（corsix/amx 官方指令测试全绿）
2. 单寄存器 `ldx/ldy` 与 pair load **均可用**（首版结论错误：早期探针装 Y[1] 却读 yoff=0）
3. pair load 在奇数 K 尾部会多读一行 → **B 打包加哨兵行**（评审用守卫页证实越界）
4. 首版 `-O3` 崩溃根因是**整数移位 UB**（`row << 56` 对 int），修复后 `-O3` 正常

## 4. 流程价值（VINW 验证点）

| 环节 | 实际发生 |
|------|---------|
| **R31 澄清**（首次实战） | L4 发现「8× vs ikj」不可达（ikj 已 23.64 GFLOPS ≈ 单核峰值 61%），升回 L1 带实测数据提问 → 用户选双基线；随后 AMX 选型再走一次澄清 → 用户选 amx-asm |
| **评审拦截** | reviewer16 抓出 6 gap + 5 inconsistency，含**我自己的错误结论**（pair-load 必需）、**隐蔽越界**（guard page 才暴露）、**验收口径不一致**（ST 门槛从未判定） |
| **诚实记录** | R4 FAIL 未修饰；AMX 三条错误结论公开更正；跨层数字口径差异被主动统一 |
| **门控生效** | L6 阶段改测试文件被 design-lag 门控拦下（前一轮 vinw-self 的教训复用） |

## 5. 遗留（下轮）

- R4 扩展性优化（MC=64 + 按算力加权分块）
- AMX 覆盖补充：回退分支、偶尾 K、大 K 正确性、EINVAL 断言、并发
- AMX 多线程（核簇共享 AMX 单元，理论上可再提速）
