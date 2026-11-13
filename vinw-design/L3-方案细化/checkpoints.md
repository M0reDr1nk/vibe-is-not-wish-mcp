---
created_at: '2026-11-13T10:02:22.740498'
layer: L3-方案细化
se_version: '2.0'
updated_at: '2026-11-13T10:02:22.740498'
---

# 设计约束与检查点

- [x] 架构决策已记录（MCP + Skill + Markdown 分层）
- [x] 接口签名已冻结（18 个 MCP tools）
- [x] 数据模型已确认（7 层目录 + manifest 状态机）
- [x] 螺旋上升机制已设计（ascend/descend/baseline 三操作）
- [x] 门控机制已设计（require/resolve confirmation）
- [x] TUI 可视化已设计（3 面板实时刷新）
- [x] 一致性检查深度：**LLM 文本审计为主，tree-sitter 强校验保留扩展能力（近期不做）**
- [x] 向量检索：**TF-IDF + ripgrep 混合方案**
- [x] 遗留项全部决策完毕