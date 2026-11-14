---
doc_type: ascensions
project: gemm
se_version: '2.0'
---

# 上升回溯记录

<!-- 每次上升操作追加记录 -->
## asc-001 [2026-11-13T17:36:31.068879+00:00]

| 字段 | 内容 |
|------|------|
| **下降轮次前** | descent-1 |
| **来源层** | L4-编码实现 |
| **目标层** | L3-方案细化 |
| **目标基线** | v001 |
| **原因** | 环境实测 Apple clang 21 不支持 -fopenmp 且无 libomp，L3 v001 的 OpenMP 并行设计无法落地；上升改设计为 pthreads 主实现 + OpenMP 可选 |
| **新下降轮次** | descent-2 |

> 上升后，L4-编码实现 至 L7 的所有工作区标记为 superseded。
