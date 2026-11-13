---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "consistency-report"
report_id: "c88f12f4"
checked_at: "2026-11-13T15:43:57.814069+00:00"
overall_status: "passed"
---

# 一致性检查报告 (c88f12f4)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | passed |
| 不一致项 | 0 |
| 匹配项 | 3 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| — | — | — | — | — | 无不一致项 | — |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| api-design.md 工具清单 | vinw/server.py | 17 个 se_* MCP 工具 | text 方法全量匹配 20/20（含 3 个提取的辅助符号） |
| api-design.md 自举加载 (v0.3) | vinw/server.py: _try_load_bootstrap_project, se_init_project adopted 分支 | _try_load_bootstrap_project | 启动探测 .vinw/manifest.md，实测加载 vinw-self-design 成功 |
| api-design.md 代码定位规则 (v0.3) | vinw/workflow/consistency_llm.py: _resolve_code_root, _collect_code_files | _resolve_code_root | manifest.code_root='..' 生效，code_scope 支持文件/目录混合 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->
