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
