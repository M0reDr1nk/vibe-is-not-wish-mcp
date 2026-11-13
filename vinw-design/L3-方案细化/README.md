---
baseline_reason: descent-5 L3：TUI 布局契约 v0.5（VerticalScroll + auto 内层 + 表格列宽 + 滚动验证契约）定稿。此前遗漏基线，由
  se_complete_project 前置校验发现
baseline_version: v006
baselined_at: '2026-11-13T16:32:53.506069+00:00'
descent_count: 0
doc_type: layer-readme
layer: L3-方案细化
rolled_back_at: '2026-11-13T16:37:44.151635+00:00'
rolled_back_from: v006
se_version: '2.0'
status: in_progress
todo_descent: 7
---

# L3-方案细化

## 当前待办

- [x] 接口设计 v0.1~v0.6（自举/一致性/完成态/TUI 布局/待办契约）
- [x] v0.7：注册表契约与 ProjectRegistry API
- [x] v0.7：MCP 每工具 project 参数 + 5 个注册表工具契约
- [x] v0.7：TUI 选择器/切换/工作目录显示 + CLI project 子命令
- [x] L3 基线化 → 下降 L4

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