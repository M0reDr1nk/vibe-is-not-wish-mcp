---
baseline_version: v014
baselined_at: '2026-11-14T09:45:47.887859+00:00'
descent_count: 1
doc_type: layer-readme
layer: L5-测试验证
se_version: '2.0'
status: baselined
todo_descent: 17
---

# L5-测试验证

## 当前待办

- [x] AC1-AC6 逐条用例覆盖
- [x] 真值表四组合验证
- [x] 门控集成（blocking 阻断 baseline/descend）
- [x] 316/316 全绿

## 阶段小结

descent-1 测试验证结果：

- **36/36 单元测试全部通过**（project:10, state_machine:13, consistency_llm:8, search:7）
- **5 个 bug 在测试轮次中修复**：frontmatter content 重复传参、LLM prompt format 失败、search frontmatter strip 报错、text 检查器表头误提取、utcnow DeprecationWarning
- **MCP tools 注册完整性验证通过**：20 个 tools 全部注册
- **TUI 启动验证通过**：SEApp 正常导入与实例化

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| v001 | — | descent-1 测试验证完成 |