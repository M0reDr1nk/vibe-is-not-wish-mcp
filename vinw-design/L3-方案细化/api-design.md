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
| `se_baseline` | layer, reason, **force** | layer, version, status；占位符未清理时返回 error（v0.6） |
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
| `se_complete_project` | — | status, completed_at, purged_confirmations；**完成态迁移（v0.4 新增，v0.6 增强）** |
| `se_purge_confirmations` | before_descent, resolution | purged, ids；**过期门控清理（v0.6 新增）** |

## TUI 布局契约（v0.5 新增）

面板必须使用 Textual 的真实滚动容器，禁止用固定高度 `Static` 直接渲染 rich `Panel`：

- 结构：`VerticalScroll`（占比 40/35/25%，带边框）包裹内层 `Static`，内层 `height: auto`
- 理由：`Static` 把 rich renderable 转成 `Visual` 时按容器高度裁剪，`virtual_size` 恒等于容器高度，`overflow-y` 因此永远不会产生可滚动内容（表现为"有数字、无滚动条、内容不全"）
- 验证契约：`vertical_scroll` 面板的 `virtual_size.height > container_size.height` 当内容溢出时；无头测试断言 `max_scroll_y > 0`
- 表格列宽：`Layer` 列需容纳最长层名（`L2-参考文献与方案搜证汇总`），超出部分 `overflow="fold"`

## 待办生命周期契约（v0.6 新增）

**核心区分**：层 README 中「## 当前待办」段属于**工作流状态**，不属于**层产物**。

1. `freeze_baseline` 仍快照 README 全文（含当时待办，作为历史证据）
2. `rollback_to_baseline` 恢复 README 时**必须保留当前现场待办段**及其 `todo_descent` 元数据——回滚是回退设计产物，不是回退工作进度
3. 实现契约：`extract_todo_section()` / `replace_todo_section()` 提供段落级切分；回滚流程 = 基线正文 + 现场待办段
4. 动机：descent-2 后 asc-002~004 每轮回滚都把 L3 待办覆盖回模板占位符

## 基线占位符守卫（v0.6 新增）

- `se_baseline(layer, reason, force=False)`：若该层 README 待办段仍含模板行 `- [ ] 初始化本层工作`，**拒绝基线**，返回 `{"error": ..., "details": [...]}`；`force=true` 显式跳过
- `se_complete_project` 前置条件追加：L1–L7 任一 README 待办仍为占位符 → 拒绝完成并列出层
- 动机：占位符可被反复冻结进基线，使「未初始化」假象成为历史证据

## 门控清理（v0.6 新增）

- 新增 `se_purge_confirmations(before_descent=0, resolution="superseded")`：把 **未解决** 且 `descent < 当前 descent` 的门控统一结转；当 `before_descent=N (N>0)` 时改为结转 `descent <= N` 的门控，返回 `{purged: n, ids: [...]}`
- `se_complete_project` 完成前自动清理「较早轮次的**非阻塞**门控」并在结果中回报 `purged_confirmations`；**blocking 门控仍阻断完成**
- 动机：descent-2 的非阻塞门控在项目完成后仍悬挂，文案过期且无法处置

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
| v0.6 | 2026-11-13 | 待办生命周期契约（回滚保留待办段）；基线占位符守卫（force 可跳过）；se_purge_confirmations 过期门控清理 | agent |
---

# v0.7 多项目跟踪管理（descent-7 / asc-006）

## 模块划分

| 模块 | 文件 | 职责 |
|------|------|------|
| 注册表 | `vinw/store/registry.py` | `~/.vinw/registry.json` 读写、探测、prune |
| 工程解析 | `vinw/store/registry.py` → `resolve_project()` | 名称/路径 → `Project` |
| MCP 工具 | `vinw/server.py` | 所有 `se_*` 增加可选 `project`；新增注册/列表/prune 工具 |
| CLI | `vinw/__main__.py` | `vinw project add/remove/list/prune` |
| TUI | `vinw/tui/app.py` + `vinw/tui/selector.py` | 工作目录显示、选择器、快捷键切换 |

## 注册表契约

```json
{
  "version": 1,
  "projects": {
    "/abs/path/to/proj": {
      "name": "proj",
      "added_at": "ISO8601",
      "last_accessed_at": "ISO8601",
      "last_seen_ok": "ISO8601",
      "missing_since": null
    }
  }
}
```

- 位置：`$VINW_HOME/registry.json`，`VINW_HOME` 缺省 `~/.vinw`
- 写入：先写 `registry.json.tmp` 再 `os.replace` 原子替换；写前重读合并，避免覆盖他人新增
- 损坏处理：JSON 解析失败 → 备份为 `registry.json.bak-<ts>` 并以空表继续，返回告警（不丢文件）

### `ProjectRegistry` API

| 方法 | 说明 |
|------|------|
| `load()` | 读注册表；损坏时备份并重建空表 |
| `save()` | 原子写 |
| `add(path, name=None)` | 探测 `.vinw/manifest.md` 后登记；重名追加 `-2` 并告警 |
| `remove(name_or_path)` | 显式移除条目（只删登记，不动磁盘） |
| `get(name_or_path)` | 返回条目或 None |
| `list(status=None)` | 全量条目 + 实时探测 `status: ok/missing`；探测结果回写 `last_seen_ok`/`missing_since` |
| `prune(missing_only=True, force=False)` | 删除 `missing` 条目；`force=False` 为 dry-run 返回将删列表 |
| `resolve(name_or_path)` | 路径优先 → 名称 → 抛 `ProjectNotFound` |

## MCP 工具契约（v0.7）

### 兼容性红线

所有既有 `se_*` 工具新增**可选**参数 `project: str | None = None`：
- `None` → 现有行为（`_active_project` 自举结果）
- 非空 → `registry.resolve(project)` 解析后使用，且**不改变** `_active_project`
- 解析失败 → `{"error": "...", "available_projects": [...]}`，绝不抛异常

### 新增工具

| 工具 | 输入 | 输出 |
|------|------|------|
| `se_register_project` | path, name(可选) | registered, name, path, status |
| `se_list_projects` | status(可选 ok/missing) | [{name, path, status, last_accessed_at}] |
| `se_remove_project` | project | removed, name |
| `se_prune_projects` | force=False | pruned, ids（dry-run 默认） |
| `se_use_project` | project | active, name, path（便于不传参的连续调用） |

## TUI 契约（v0.7）

- 顶部 header 常显两行：`工作目录: <cwd>` / `当前工程: <name> @ <path>`
- 无参启动 → `ProjectSelector` 模态：列出注册表条目（含 `missing` 灰显）+ 「当前目录工程」项；空表时显示引导文案与 `vinw project add .` 提示
- 快捷键：`p` 切换工程（打开选择器）、`r` 强制刷新、`q` 退出
- 切换后：所有面板立即重绘，header 同步更新；不重启进程

## CLI 契约（v0.7）

```
vinw project add <path> [--name NAME]
vinw project list [--missing]
vinw project remove <name|path>
vinw project prune [--force]
vinw tui [<path|name>]     # 无参 → 选择器
```

## 版本历史补充

| v0.7 | 2026-11-13 | 多项目跟踪管理：注册表模块、MCP 每工具 project 参数 + 5 个注册表工具、TUI 选择器与切换、CLI project 子命令 |
| v0.8 | 2026-11-14 | 注册表存储改为 SQLite（控制面/数据面分层、projects + project_events、WAL、JSON 迁移与导出、state 意图与观测分离） |

---

# v0.8 注册表改用 SQLite（descent-8 / asc-007）

## 分层原则

- **控制面**：`$VINW_HOME/registry.db`（SQLite，WAL）——工程清单、状态、状态切换事件
- **数据面**：`<工程>/.vinw/*.md`（Markdown + frontmatter）——完全不变

## Schema（`PRAGMA user_version = 2`）

```sql
CREATE TABLE IF NOT EXISTS projects (
  path             TEXT PRIMARY KEY,              -- 规范化绝对路径
  name             TEXT NOT NULL UNIQUE,          -- 唯一别名
  state            TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active','dormant')),
  added_at         TEXT NOT NULL,
  last_accessed_at TEXT,
  last_seen_ok     TEXT,
  missing_since    TEXT                           -- NULL = 正常；非空 = 观测失效
);

CREATE TABLE IF NOT EXISTS project_events (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  path   TEXT NOT NULL,
  event  TEXT NOT NULL,   -- register|remove|activate|deactivate|missing|recover|import
  at     TEXT NOT NULL,
  detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_path ON project_events(path, id DESC);
```

连接参数：`journal_mode=WAL`、`busy_timeout=5000`、`foreign_keys=ON`；每次操作用短连接（`with self._connect() as conn`）。

## 状态语义（intent 与 observation 分离）

| 字段 | 语义 | 写入者 |
|------|------|--------|
| `state` | **用户声明的意图**：`active`（在关注）/ `dormant`（休眠） | 用户（`vinw project activate/deactivate`） |
| `missing_since` / `last_seen_ok` | **系统观测的现实** | 探测逻辑 |

探测策略：
- `list(probe=None)` 默认**只探测 `active`**；`dormant` 返回缓存状态并置 `probed: false`
- `list(probe=True)` 强制全量探测；`list(probe=False)` 完全不探测
- 探测引发 `ok→missing` 或 `missing→ok` 转变时写一条 `project_events`（`missing` / `recover`）

## 写策略

- `touch()` → 单行 `UPDATE projects SET last_accessed_at=?`（微秒级，无需去抖）
- 不再有整表重写；并发安全由 WAL + busy_timeout 保证

## 迁移（JSON → SQLite）

首次打开时若 `registry.db` 不存在且 `registry.json` 存在：
1. 逐条导入 `projects`（`state` 默认 `active`，`missing_since` 沿用）
2. 每条写 `project_events(event='import')`
3. 原文件重命名为 `registry.json.migrated-<ts>`（保留，不删除）
4. 迁移失败整体回滚（事务），原 JSON 不动

## API（`ProjectRegistry` 对外签名保持兼容）

| 方法 | 变化 |
|------|------|
| `load/save` | 内部改为 SQL，对外不再暴露（保留 `export_json()` 供人读） |
| `add/remove/get/list/resolve/describe` | 签名不变 |
| `prune(missing_only, force)` | 语义不变（默认 dry-run） |
| `touch(name_or_path)` | 单行 UPDATE |
| **新增** `set_state(name_or_path, state)` | active/dormant 切换 + 事件 |
| **新增** `history(name_or_path, limit=20)` | 状态切换记录 |
| **新增** `export_json()` | 导出快照供人查看/备份 |

## CLI / MCP 增量

| 命令 | 说明 |
|------|------|
| `vinw project activate <target>` / `deactivate` | 状态切换 |
| `vinw project history <target>` | 状态切换记录 |
| `vinw project export [--out FILE]` | JSON 快照（默认 stdout） |
| `se_set_project_state`（MCP） | 状态切换 |
| `se_project_history`（MCP） | 记录查询 |

## 兼容红线

- `list()` 返回结构保持 `{name, path, status, ...}`，新增字段（`state`, `probed`）只增不改
- `prune` 仍默认 dry-run、永不静默删除
- 工程内 Markdown 与全部既有工具行为不变
