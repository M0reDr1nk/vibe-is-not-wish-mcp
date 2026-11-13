---
baseline_reason: descent-8 L3 v0.8：SQLite 注册表 schema/迁移/状态语义/API 增量设计定稿（门控 cfm-...-005
  非阻塞供审阅）
baseline_version: v010
baselined_at: '2026-11-13T17:01:09.397664+00:00'
descent_count: 0
doc_type: layer-readme
layer: L3-方案细化
rolled_back_at: '2026-11-13T17:16:46.739191+00:00'
rolled_back_from: v010
se_version: '2.0'
status: in_progress
todo_descent: 8
---

# L3-方案细化

## 当前待办

- [x] 接口设计 v0.1~v0.7（自举/一致性/完成态/TUI/待办契约/多项目）
- [x] v0.8：SQLite schema（projects + project_events、WAL、user_version=2）
- [x] v0.8：state(intent)/missing_since(observation) 分离与探测策略
- [x] v0.8：JSON→SQLite 迁移、export_json、history、set_state
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