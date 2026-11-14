---
baseline_reason: descent-14 L3 v0.16：全阶段审计契约（任何转换漂移后必须出示匹配当前设计与代码的结论）
baseline_version: v018
baselined_at: '2026-11-14T06:01:19.777322+00:00'
descent_count: 0
doc_type: layer-readme
layer: L3-方案细化
rolled_back_at: '2026-11-14T05:07:28.906056+00:00'
rolled_back_from: v016
se_version: '2.0'
status: superseded
todo_descent: 10
---

# L3-方案细化

## 当前待办

- [x] 接口设计 v0.1~v0.9（自举/一致性门控/多项目/SQLite/待审呈现）
- [x] v0.10：符号提取模块 symbols.py 契约 + 语言规则表
- [x] v0.10：TextConsistencyChecker 改造（扩展名/空扫描报错/双语交集）
- [x] v0.10：门控异常分类（PlaceholderTodoError / ConsistencyGateError）
- [ ] 等待审批 → 基线 L3 → 下降 L4
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