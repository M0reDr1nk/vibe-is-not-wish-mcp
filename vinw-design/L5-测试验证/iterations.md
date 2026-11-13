---
se_version: "2.0"
layer: "L5-测试验证"
doc_type: "iterations"
---

# 测试-修复迭代记录

| 轮次 | 测试结果 | 发现问题 | 修复方案 | 再测试结果 |
|------|---------|---------|---------|-----------|
| descent-2 r1 | 45/45 PASS | 一致性检查在自举场景误报 20 符号缺失（代码根固定为项目根 + code_scope 不支持文件条目） | manifest.code_root + _resolve_code_root/_collect_code_files（chg-...-022） | 45/45 PASS，MCP 实测 20/20 匹配 |
| descent-3 r1 | 52/52 PASS | descent-2 终验后三项热修游离于流程外（无上升记录、终验失真） | asc-002 上升回 L3，descent-3 重新基线并补录测试证据 | 52/52 PASS |
| descent-4 r1 | 55/55 PASS | 终验完成后 L7 永远 in_progress（mark_layer_completed 无 MCP 出口）；TUI 滚动条修复未安装 | 新增 se_complete_project（v0.4 设计）+ TUI completed 渲染；重装 .venv | 55/55 PASS |
| descent-5 r1 | 56/56 PASS | TUI 面板无真实滚动内容（固定高度 Static 裁剪 rich Visual，max_scroll_y 恒 0）；待办表格列宽截断 | VerticalScroll + auto 高度内层 Static；表格 expand/fold 重做；新增滚动断言测试 | 56/56 PASS |
| descent-6 r1 | 71/71 PASS | 三项结构性缺陷（回滚倒带待办/占位符可入基线/过期门控悬挂） | L3 v0.6 设计 → 实现守卫与清理工具；旧用例适配 | 71/71 PASS |
| descent-7 r1 | 101/101 PASS | 多项目能力缺失（单活动工程、TUI 单路径） | L1-L3 扩展设计 → registry 模块 + 每工具 project 参数 + TUI 选择器 + CLI | 101/101 PASS |
| descent-8 r1 | 112/112 PASS | 注册表 JSON 无并发锁、写放大 9.5ms/次、存储选型权重错配 | SQLite（WAL+事务+单行 UPDATE）+ intent/observation 分离 + 迁移与容错 | 112/112 PASS |
