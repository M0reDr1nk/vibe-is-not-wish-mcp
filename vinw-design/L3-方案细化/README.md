---
baseline_reason: descent-21 L3 v023：接管现有代码仓设计（v0.23）；转换点审计 report-77fc78a2-01（2 项
  design-ahead GAP 为预期内）
baseline_version: v024
baselined_at: '2026-11-21T14:19:16.017611+00:00'
descent_count: 0
doc_type: layer-readme
layer: L3-方案细化
rolled_back_at: '2026-11-21T14:17:47.684564+00:00'
rolled_back_from: v023
se_version: '2.0'
status: baselined
todo_descent: 22
---

# L3-方案细化

## 当前待办

- [x] asc-021 上升回 L3（descent-22）：INC-002/003/005 措辞对齐
- [x] design-doc/api-design 措辞修订（work 替换语义+special 全层、hint 窄化、错误文案模板）
- [ ] L3 v024 基线 → 下降 L4（重做）→ 重锚审计 → L4 v020 基线 → L5

- [x] changelog extra 字段与转义规则
- [x] 共享解析器契约（围栏/反引号/分隔符/类型）
- [x] alignment 9 字段定义
- [x] 向后兼容与边界
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