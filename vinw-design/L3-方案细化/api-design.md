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
| `se_init_project` | name, path, description | project_id, layers, current_layer, descent |
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

## 版本历史

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| v0.1 | 2026-11-13 | 初始设计 | agent |
| v0.2 | 2026-11-13 | 增加 L2 层 + 螺旋上升 | agent |