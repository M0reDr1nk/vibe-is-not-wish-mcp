---
baseline_reason: descent-3 L1 v003：性能基线口径修订（用户裁定 both-baselines + AMX 追加裁定），验收尺寸固定
  1024³，R3/R4 门槛可机器判定
baseline_version: v002
baselined_at: '2026-11-14T08:26:54.270894+00:00'
descent_count: 0
doc_type: layer-readme
layer: L1-需求拆解
rolled_back_at: '2026-11-14T09:53:31.803834+00:00'
rolled_back_from: v002
se_version: '2.0'
status: in_progress
todo_descent: 1
---

# L1-需求拆解

## 当前待办

- [x] 原始需求录入 proposals.md
- [x] 拆解为 R1-R7 七项子需求（接口/正确性/单线程/多线程/基准/可移植/构建）
- [x] 明确非目标（无 FP16/GPU/batched/转置）与 Q1-Q6 问题域
- [x] 定义验收方式（make test / make bench / 8x 加速门槛）
## 阶段小结

（阶段完成时填写）

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| — | — | — |