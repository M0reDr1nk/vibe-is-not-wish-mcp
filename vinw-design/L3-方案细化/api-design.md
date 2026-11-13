---
created_at: '2026-11-13T10:02:22.615842'
layer: L3-方案细化
se_version: '2.0'
updated_at: '2026-11-13T10:02:22.615842'
---

# 接口设计

## MCP 工具清单（18个）

### 项目生命周期

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_init_project` | name, path, description | project_id, layers, current_layer, descent；**若目标已含 `.vinw/manifest.md` 则接管（adopted=true）** |
| `se_get_project` | — | full state + layer_graph + ascent_history + pending |

### 基线管理

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_baseline` | layer, reason | layer, version, status |
| `se_list_baselines` | layer(可选) | {layer: [versions]} |

### 上升/下降

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_ascend` | from_layer, to_layer, to_baseline, reason | ascent_id, new_descent |
| `se_descend` | to_layer, reason | from_layer, to_layer, current_descent |
| `se_can_descend` | — | can_descend, message, next_layer |

### 门控确认

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_require_confirmation` | item_type, description, options, blocking | confirmation_id |
| `se_resolve_confirmation` | confirmation_id, resolution, feedback | id, resolution |

### 文档 CRUD

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_store_document` | layer, filename, content, doc_type | path, status |
| `se_read_document` | layer, filename | frontmatter + content |
| `se_list_documents` | layer(可选) | {layer: [filenames]} |

### 变更追踪

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_log_change` | change_type, scope, reason, before, after | change_id |
| `se_get_changelog` | limit | {entries: [...]} |

### 一致性检查

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_check_consistency` | design_layer, design_doc, code_scope, method="llm" | report_id, matched, inconsistencies, overall |

`method` 参数:
- `"llm"` (默认): 将设计文档 + 代码全文传给 LLM 做语义级比对，返回结构化报告
- `"text"`: 本地文本字符串匹配（函数名存在性检查），无 LLM 依赖
- `"ast"`: tree-sitter AST 结构化比对（**预留扩展**，当前 fallback 到 llm）

报告格式写入 `L4-编码实现/consistency-reports/report-{id}.md`。

**代码定位规则（v0.3 修订）**：
- manifest 支持可选字段 `code_root`：代码仓根目录，相对项目根解析（自举场景下设计工程位于代码仓子目录，如 `".."`）；缺省默认为项目根本身
- `code_scope` 支持文件与目录混合：文件条目直接纳入扫描，目录条目递归 `rglob("*.py")`；`code_scope` 为空时扫描 `code_root`（若存在 `code_root/src` 则仅扫描 `src`）

### 方案检索（L2 层）

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_search_proposals` | query, search_scope="local", method="rg" | [{source, relevance, excerpt}] |

`search_scope`:
- `"local"`: 当前项目的历史层文档
- `"archive"`: 指定的历史项目归档目录

`method`:
- `"rg"` (默认): ripgrep 文本搜索，按关键词匹配
- `"tfidf"`: TF-IDF 余弦相似度排序（历史项目 > 50 个时自动建议切换）

### Todo 管理

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_get_todos` | — | [{layer, descent, done, text}] |
| `se_update_todo` | layer, todos_json | layer, todo_count |

### 指导

| 接口名 | 输入 | 输出 |
|--------|------|------|
| `se_get_next_steps` | — | current_layer, suggested_work, gate, can_descend, special_instruction |
| `se_complete_project` | — | status, completed_at；**完成态迁移（v0.4 新增）** |

## TUI 布局契约（v0.5 新增）

面板必须使用 Textual 的真实滚动容器，禁止用固定高度 `Static` 直接渲染 rich `Panel`：

- 结构：`VerticalScroll`（占比 40/35/25%，带边框）包裹内层 `Static`，内层 `height: auto`
- 理由：`Static` 把 rich renderable 转成 `Visual` 时按容器高度裁剪，`virtual_size` 恒等于容器高度，`overflow-y` 因此永远不会产生可滚动内容（表现为"有数字、无滚动条、内容不全"）
- 验证契约：`vertical_scroll` 面板的 `virtual_size.height > container_size.height` 当内容溢出时；无头测试断言 `max_scroll_y > 0`
- 表格列宽：`Layer` 列需容纳最长层名（`L2-参考文献与方案搜证汇总`），超出部分 `overflow="fold"`

## 完成态迁移（v0.4 新增）

`se_complete_project` 将项目从 L7-终验 in_progress 迁移到 completed：

- 前置校验：当前层必须为 L7-终验；L1–L6 全部 baselined；无未解决的 blocking 门控（不满足返回结构化 error，不抛异常）
- 动作：L7 README frontmatter `status=completed`；manifest `layer_states[L7].status="completed"`、`completed_at=now(UTC)`
- 前置校验失败时返回 `{"error": ...}` 及未满足项清单，由 agent 修正后重试
- 动机：descent-3 终验后状态停留在 in_progress，完成语义此前无 MCP 出口

## 自举加载（Bootstrap，v0.3 新增）

Server 启动时自动探测并加载活动工程，实现 VINW 自举（在自身代码仓中运行 `vinw server` 即可管理自身设计工程）：

1. 探测顺序：`cwd/vinw-design/.vinw/manifest.md` → `cwd/.vinw/manifest.md`
2. 命中即作为 `_active_project`，所有工具开箱可用，无需先调用 `se_init_project`
3. 未命中则维持 `None`，工具返回 "No active project. Call se_init_project first."
4. `se_init_project` 在目标目录已有 `.vinw/manifest.md` 时不再报错，而是接管该工程并返回 `adopted=true` 及其实际 current_layer/descent

约束：`_active_project` 为进程内单例（简化设计），后续版本支持 project_id 多工程映射。

## 版本历史

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| v0.1 | 2026-11-13 | 初始设计 | agent |
| v0.2 | 2026-11-13 | 增加 L2 层 + 螺旋上升 | agent |
| v0.3 | 2026-11-13 | 自举加载：启动自动探测工程 + se_init_project 接管已有工程；一致性检查代码定位规则（manifest.code_root + code_scope 混合文件/目录）；**状态目录统一更名 `.se/` → `.vinw/`**（经门控 modify 反馈批准） | agent |
| v0.4 | 2026-11-13 | 新增 se_complete_project 完成态迁移（终验闭环出口）；TUI 增加 completed 状态渲染 | agent |
| v0.5 | 2026-11-13 | TUI 布局契约：VerticalScroll + auto 高度内层 Static（修复固定高度 Static 无真实滚动内容）；表格列宽约束 | agent |