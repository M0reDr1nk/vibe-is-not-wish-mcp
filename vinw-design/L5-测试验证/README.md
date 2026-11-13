---
descent_count: 1
doc_type: layer-readme
layer: L5-测试验证
se_version: '2.0'
status: in_progress
todo_descent: 6
---

# L5-测试验证

## 当前待办

- [x] 测试计划与用例演进（descent-1~6）
- [x] 新增 test_todo_lifecycle.py 15 例（段落切分/回滚保留待办/占位符守卫/门控清理/完成态守卫）
- [x] 旧用例适配守卫行为（机制类 baseline 显式 force=True）
- [x] 全量 71/71 通过
- [x] 测试结果与迭代记录已更新（descent-6 round 1）

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