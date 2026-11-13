---
baseline_reason: descent-4 L3：v0.4 完成态迁移设计（se_complete_project 前置校验与动作）
baseline_version: v005
baselined_at: '2026-11-13T16:26:30.229108+00:00'
descent_count: 0
doc_type: layer-readme
layer: L3-方案细化
rolled_back_at: '2026-11-13T16:31:32.500265+00:00'
rolled_back_from: v005
se_version: '2.0'
status: in_progress
---

# L3-方案细化

## 当前待办

- [ ] 初始化本层工作

## 阶段小结

（阶段完成时填写）

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| — | — | — |

## 已决策遗留项

| 遗留项 | 决策 | 理由 |
|--------|------|------|
| 一致性检查深度 | **LLM 文本审计为主**，tree-sitter 强校验保留扩展能力（近期不做） | LLM 能捕捉语义级不一致；tree-sitter 作为接口签名漂移的备用防火墙，启用条件：连续 2 次以上因签名不一致触发 ascend |
| 向量检索 | **TF-IDF + ripgrep** | 当前规模下 faiss 过度设计；ripgrep 零成本，TF-IDF 在历史项目 > 50 个时无缝升级 |