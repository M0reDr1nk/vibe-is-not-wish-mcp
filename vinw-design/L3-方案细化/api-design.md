---
created_at: '2026-11-13T10:02:22.615842'
layer: L3-方案细化
se_version: '2.0'
updated_at: '2026-11-13T10:02:22.615842'
---

# 接口设计

## MCP 工具清单（共 36 个，由 scripts/gen_tool_catalog.py 生成）

> 生成方式：解析 `vinw/server.py` 中所有 `se_*` 函数；`tests/test_contract_v014.py` 断言此处条目数 == 实际注册数。

| 工具 | 输入 | 输出 |
|------|------|------|
| `se_ascend` | — | — |
| `se_baseline` | — | — |
| `se_can_descend` | — | — |
| `se_check_consistency` | — | — |
| `se_complete_project` | — | — |
| `se_descend` | — | — |
| `se_export_projects` | — | — |
| `se_get_changelog` | — | — |
| `se_get_escalations` | — | — |
| `se_get_next_steps` | — | — |
| `se_get_project` | — | — |
| `se_get_todos` | — | — |
| `se_init_project` | — | — |
| `se_list_baselines` | — | — |
| `se_list_documents` | — | — |
| `se_list_projects` | — | — |
| `se_log_change` | — | — |
| `se_project_history` | — | — |
| `se_prune_projects` | — | — |
| `se_purge_confirmations` | — | — |
| `se_read_document` | — | — |
| `se_record_triage_decision` | — | — |
| `se_register_project` | — | — |
| `se_remove_project` | — | — |
| `se_repair_state` | — | — |
| `se_require_confirmation` | — | — |
| `se_resolve_confirmation` | — | — |
| `se_search_proposals` | — | — |
| `se_set_project_state` | — | — |
| `se_store_consistency_report` | — | — |
| `se_store_document` | — | — |
| `se_store_triage` | — | — |
| `se_sync_layer_readmes` | — | — |
| `se_triage_prompt` | — | — |
| `se_update_todo` | — | — |
| `se_use_project` | — | — |

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
| 工程解析 | `vinw/store/registry.py` → `ProjectRegistry.resolve()` | 名称/路径 → `Project` |
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

### `ProjectRegistry` API（v0.8 起为 SQLite 实现，读写走内部事务连接）

| 方法 | 说明 |
|------|------|
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
| v0.9 | 2026-11-14 | 一致性校验门控：指纹增量判定（fresh/stale_files/stale_design/missing）、三处触发点、自动 text 兜底；非阻塞门控分类呈现；设计评审门控默认阻塞 |
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
| （已移除）读/写方法 | 随 v0.8 SQLite 迁移删除；改为内部事务连接 + `export_json()` 导出 |
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

---

# v0.9 一致性校验门控（descent-9 / asc-008）

## 问题

1. `se_check_consistency` 纯自觉调用：`baseline()` / `descend()` / `se_complete_project()` 均不校验，漏做无任何提示
2. 报告不记 `descent` 与代码指纹 → 无法判断"本轮代码是否被检查过"，也无法判断"检查后代码是否又改了"
3. 非阻塞门控遗留项在各视图中呈现不直观（与普通待办混排，无"待你处置"分组）

## 设计原则

**代码由 agent 直接写盘、不经 MCP**，无法拦截每次写入。因此采用「**指纹 + 转换点门控 + 自动兜底**」：所有推进路径都过门控，门控处比对指纹，逻辑上等价于必然触发。

## 指纹契约

检查时记录（写入报告 frontmatter）：

| 字段 | 说明 |
|------|------|
| `descent` | 检查发生时的下降轮次 |
| `scope` | 扫描范围（`["vinw"]` 等） |
| `design_hash` | 设计文档内容 sha256 |
| `file_hashes` | `{相对路径: sha256}`，逐文件 |
| `code_fingerprint` | `sha256(sorted(file_hashes))` —— **v0.15 起仅含代码**；设计摘要独立在 `design_hash`，两者不再混算 |

## 新鲜度判定（增量，避免重复检查）

`ConsistencyGate.freshness(scope, design_doc)` 三态：

| 状态 | 条件 | 门控行为 |
|------|------|---------|
| `fresh` | 本轮存在 passing 报告，且 `code_fingerprint` 与当前一致 | **直接放行，零成本**；`se_check_consistency` 返回 `reused: true` + 上次结论 |
| `stale_files` | 设计未变，部分代码文件增删改 | 自动跑 **text 检查**（毫秒级，写入新报告）后判定 |
| `stale_design` | `design_hash` 变化 | text 检查 + 提示需 `method="llm"` 语义重审 |
| `missing` | 本轮无 passing 报告 | 自动跑 text 检查后判定 |

**为什么 text 每次全量扫**：symbol 存在性检查是跨文件的（符号可能移文件），按文件增量会误报缺失；而其成本是毫秒级，全量扫更正确也更简单。**真正昂贵的是 LLM 语义审计**，故增量只作用于 `method="llm"`：fresh 时直接复用结论，不重复构造/消耗审计。

## 门控触发点（三处全覆盖）

| 触发点 | 位置 | 行为 |
|--------|------|------|
| ① L4 基线 | `WorkflowEngine.baseline("L4-编码实现")` | `gate.ensure()`：非 fresh → 自动 text 检查并落盘；`overall != passed` → 拒绝基线（`force=True` 可跳过） |
| ② L4→L5 下降 | `WorkflowEngine.descend("L5-测试验证")` | 同上，防绕过 ① |
| ③ 完成 | `se_complete_project` | 校验本轮 L4 存在 passing 报告，否则列入 details |

## 状态记录（可观测）

- `manifest.layer_states["L4-编码实现"]["consistency"] = {report_id, overall, descent, checked_at, code_fingerprint}`
- `se_get_project` 输出该字段；TUI 层图显示 `✓chk` 标记与过期提示

## 非阻塞门控呈现改进

| 视图 | 变化 |
|------|------|
| `se_get_project` | 拆分 `blocking_pending` / `pending_review`（后者含 id/layer/item_type/description/age_days） |
| `se_get_next_steps` | 新增 `awaiting_review` 字段（即使当前层无待办也会列出） |
| TUI 待办面板 | 分两组：`🔒 阻塞（会卡流程）` / `🔓 待你审阅（不卡流程）`，标题显示两个计数 |
| `se_complete_project` 结果 | 回报 `pending_review`（不阻断，但显式列出） |

## 设计评审门控语义（约定 + 校验）

- `requirement-decomposition` / `interface-design` 类门控**默认阻塞**（它们的作用就是拦住实现）
- `se_require_confirmation` 对这两类 `item_type` 在未显式传 `blocking` 时默认 `True`
- 其余类型（test-results 等）默认 `False`，作为"知会式审阅"

---

# v0.10 跨语言一致性检查（descent-10 / asc-009）

## 配置契约（manifest）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code_extensions` | list[str] | `[".py",".c",".h",".cc",".cpp",".hpp",".rs",".go",".java",".ts",".tsx",".js"]` | 参与一致性检查的代码扩展名（补入 .tsx/.js，见 v0.13 节） |
| `code_root` | str | `"."` | 代码根（相对工程根） |

## 模块契约

### `vinw/workflow/symbols.py`（新增）

| 函数 | 签名 | 说明 |
|------|------|------|
| `extract_code_symbols` | `(path: Path) -> set[str]` | 按扩展名选规则提取定义符号 |
| `filter_symbols` | `(names: Iterable[str]) -> set[str]` | 过滤语言关键字与保护宏 |
| `extract_design_identifiers` | `(content: str) -> set[str]` | 从设计文档提取候选标识符（反引号/表格/代码块） |

语言规则表：`LANGUAGE_RULES: dict[str, list[re.Pattern]]`，键为扩展名。
- Python: `def` / `class` / `NAME =`（模块级常量可选）
- C/C++: 函数定义 `\b(\w+)\s*\([^;{]*\)\s*\{`；函数声明 `\b(\w+)\s*\([^;{]*\)\s*;`（仅头文件）；`#define NAME`
- Rust: `fn NAME` / `struct NAME` / `enum NAME`
- Go: `func NAME` / `type NAME`
- Java/TS: `class|interface|function NAME`

### 设计侧符号的 required / advisory 二分（v0.13 补入，descent-12 裁定 INC-005）

设计文档中出现的标识符并非都要求代码实现。判定规则：

| 类别 | 判定条件 | 缺失后果 |
|------|---------|---------|
| **required** | ① API 表（表头含 接口/工具/函数/命令/方法/API/endpoint）**首列**的首个标识符；② 单列表格中的标识符；③ `foo(...)` 调用形式（且含下划线）；④ 代码围栏中的 `def/fn/func/class/struct/interface` 签名 | **阻塞**（计入 inconsistencies） |
| **advisory** | 其他反引号标识符：配置键、状态机取值、JSON 字段名、prose 提及、SQL/JSON 围栏内容 | 仅列入 `advisory_missing`，**不阻塞** |

理由：不加二分时，本项目实测产生 73 项假阳性（`kind`/`gaps`/`dormant`/`Panel` 等配置键、枚举值与第三方类名），门控失去意义。
过滤规则同时覆盖：语言关键字、头文件保护宏（`FOO_H`）、保留标识符（`_OPENMP`）、版本号（`v0`）、标准库/内置函数、模块与 SQL 对象名。

### `TextConsistencyChecker.check()` 改造

1. 用 `code_extensions` 收集文件（替代写死 `*.py`）
2. `files_scanned == 0` → 返回 `{"error": "no code files matched", "extensions": [...], "code_root": ...}`（**不产出报告**）
3. 代码侧符号集 = 所有文件符号并集
4. 设计侧符号集 = `extract_design_identifiers()` 过滤后
5. 缺失项 = 设计侧 − 代码侧；匹配项 = 交集（各带首个出现位置）
6. 返回增加 `files_scanned` / `extensions` / `code_symbols_count`

### `store_report()` 增加字段

`files_scanned`、`extensions`、`code_symbols_count`（写入 frontmatter，可供门控与人工核对）

## 门控异常契约

| 异常类 | 触发 | 对应 hint |
|--------|------|-----------|
| `PlaceholderTodoError(ValueError)` | 待办仍为模板占位符 | 调用 se_update_todo 填写真实待办，或 force=true |
| `ConsistencyGateError(ValueError)` | 一致性门控未通过 | 查看 consistency-reports/ 最新报告；修复后重试或 force=true |

`se_baseline` 按异常类型返回对应 hint，不再写死。

## 兼容性

- 报告结构与既有字段保持（`overall_status`/`inconsistencies`/`matched`）
- 指纹机制不变：`file_hashes` 覆盖新扩展名的文件
- Python 工程行为不变（回归测试保障）

## 版本历史

| v0.10 | 2026-11-14 | 跨语言一致性检查：code_extensions 配置、双语符号交集、关键字/保护宏过滤、空扫描报错、门控异常分类 |

---

# v0.11 分层审计契约（descent-11 / asc-010）

## 策略配置（manifest）

| 字段 | 取值 | 默认 | 含义 |
|------|------|------|------|
| `consistency_policy` | `text` / `text+llm` / `strict` | `text+llm` | 各处门控要求的审核深度 |
| `consistency_auditor` | `self` / `reviewer` | `reviewer` | 期望审查者类型（写入报告） |

政策矩阵：

| 触发点 | `text` | `text+llm` | `strict` |
|--------|--------|-----------|----------|
| `se_baseline(L4)` | text | text | text + llm |
| `se_descend(L4→L5)` | text | **text + llm** | text + llm |
| `se_complete_project` | text | **text + llm** | text + llm |

## 报告类型（`kind`）与新增元数据

| 字段 | 说明 |
|------|------|
| `kind` | `text`（门控自动/R文本方法） / `llm`（语义审核结论入库） |
| `policy` / `auditor` / `auditor_model` | 产生时的策略与审查者 |
| `llm_verdict` | `passed/warning/failed` |
| `gaps` | 缺口清单（设计要求但缺代码/缺测试） |
| `tooling_discrepancy` | text 与 LLM 结论冲突标记 |

`latest_passing(descent, kind=None)` 按 kind 过滤。

## LLM 审核输出 schema（v2）

```json
{
  "overall": "passed|warning|failed",
  "gaps": [{"id":"GAP-001","design_ref":"api-design.md:42","missing":"code|test",
            "description":"...","severity":"critical"}],
  "inconsistencies": [{"id":"INC-001","category":"logic|data_model|interface|constraint",
            "design_ref":"design-doc.md:31","code_ref":"src/x.c:120",
            "description":"...","suggestion":"..."}],
  "matched": [{"design_ref":"...","code_ref":"...","symbol":"...","note":"..."}]
}
```

每条结论必须带 `design_ref`，尽可能带 `code_ref`；无证据条目视为无效。

## 门控行为

```
ensure(kind="text"): 指纹判定 → 非 fresh 跑 text 并落盘 kind=text
llm_status(): policy != "text" → 查 latest_llm(descent)
              ⚠ 本节为 v0.11 旧口径，已被 v0.14 §3 取代：
              以 present + matches_current 判定 satisfied，不再看 overall
tooling_discrepancy: 最新 text=warning 且同指纹 llm=passed → 拒绝放行并列冲突原因
```

## 接口增量

| 接口 | 变化 |
|------|------|
| `se_check_consistency(method="llm")` | 返回 v2 prompt（缺口清单 + 实现一致性两部分） |
| `se_store_consistency_report` | 新增 `auditor`/`auditor_model`；自动 kind=llm，写 llm_verdict/gaps |
| `se_get_project.consistency` | 增加 `llm_verdict`/`policy`/`needs_llm` |

---

# v0.12 审计分级裁定（descent-12 / asc-011）

## 数据模型

LLM 报告的每条 `inconsistencies` / `gaps` 增加：

| 字段 | 取值 | 必填 |
|------|------|------|
| `classification` | `impl_bug` / `design_bug` / `design_gap` / `ambiguous` | 由**裁定阶段**必填；审计报告本身可不含 |
| `confidence` | `high` / `medium` / `low` | 同上 |
| `recommendation` | 推荐处置文本 | 同上 |
| `status` | `open` / `fixed` / `decided` / `accepted` | 由系统维护 |

## 裁定提示词（**不入 PROMPT_TEMPLATE**，由 `se_triage_prompt` 单独下发）

> v0.14 §6 已裁定：审计与裁定分两轮。审计 prompt 保持 v2（只描述缺口与偏差），
> 裁定问题（classification/confidence/recommendation）由 `se_triage_prompt` 提供。

```
对每条发现，先判断"设计本身是否合理"，再判断"实现是否偏离设计"：
1. 设计不合理/过时/自相矛盾 → design_bug 或 design_gap
2. 设计合理而实现偏离       → impl_bug
3. 涉及外部契约、命名偏好、优先级等需权衡 → ambiguous
4. confidence=high 必须能给出明确证据（行号 + 推理链）；证据不足时降为 medium
禁止默认把不一致判为 impl_bug。
```

## 门控判定

`ConsistencyGate.triage_decision()` 返回：

| decision | 条件 | 门控行为 |
|----------|------|---------|
| `auto_fixable` | 全部 finding 为 `impl_bug` 且 `confidence=high` 且 `status != open` | 放行 |
| `auto_fix_pending` | 全部为 impl_bug/high，但仍有 `open` | 阻断，提示可自动修正 |
| `escalate` | 存在 `design_*` / `ambiguous`，或 impl_bug 置信度非 high，且未裁定 | 阻断，返回升级项 |
| `clear` | 无 findings | 放行 |

## 新工具

| 工具 | 输入 | 输出 |
|------|------|------|
| `se_triage_prompt` | project | 返回裁定提示词 + 现有 findings（供 reviewer 作答） |
| `se_store_triage` | report_json | 写入图文裁定（classification/confidence/recommendation） |
| `se_get_escalations` | project | 待用户裁决项：finding_id、difference、analysis、recommendation、impact |
| `se_record_triage_decision` | finding_id, decision, note | 记录用户裁定；decision ∈ fix_impl / fix_design / accept_as_is / defer |

裁决以 `decision` 映射 `status`：`fix_impl`→`fixed`（需配合 se_log_change），`fix_design`→`decided`，`accept_as_is`→`accepted`，`defer`→保持 `open`。

## 持久化

- LLM 报告 frontmatter：`triage: [{id, classification, confidence, recommendation, status}]`
- manifest：`layer_states[L4].audit = {report_id, decision, escalations: [finding_id...], escalations_count, auto_fixable: [finding_id...], auto_fixable_count}`（v0.14 起统一为列表 + 计数，二者对称）

## 与既有契约的关系

- 不改变 text 门控与指纹缓存的语义
- `se_complete_project` / `descend(L4→L5)` 增加 `triage_decision()` 校验
- 升级项不写进 `pending_confirmations`（避免与人工门控混淆），由 `se_get_escalations` 统一管理

## 版本历史

| v0.12 | 2026-11-14 | 审计分级裁定：classification/confidence/recommendation、triage 门控决策、4 个新工具 |

---

# v0.14 审计契约补全（descent-13 / asc-012）

> 本版回应 reviewer2 的 9 项设计侧发现（GAP-001~005、INC-005/007/009/012）。
> 原则：**先补契约，再改实现**；实现侧改动见 L4 implementation.md。

## 1. 漂移检测契约（GAP-001）

### 数据模型 `drift`

| 字段 | 类型 | 语义 |
|------|------|------|
| `state` | `clean` / `drifted` / `design_lag` / `design_synced` / `unknown` | **五态**（v0.14 §9 起）。`unknown` 表示无法判定，**不得等同于 clean** |
| `detected` | bool | 等价于 `state == "drifted"`（仅此一态） |
| `needs_reaudit` | bool | `state != "clean"` 时为真：需要重新审计 |
| `reason` | str | `in_sync` / `code_changed_without_design_update`（→design_lag）/ `code_and_design_changed_since_audit`（→design_synced）/ `design_changed_since_audit`（→drifted）/ `code_changed_since_audit_design_unknown`（→drifted）/ `no_audited_fingerprint` / `unavailable: ...` |
| `changed` | list[str] | 变更条目，格式 `added|removed|modified:<相对路径>`；无审计哈希时为空 |
| `baseline_fingerprint` | str \| null | 最近一次通过审计的指纹 |
| `current_fingerprint` | str \| null | 当前工作区指纹 |
| `audited_report` | str \| null | 对应的审计报告 id |

### 呈现契约

- `se_get_project.drift` 输出上述结构
- TUI：`drifted` → 红色「⚠ 漂移告警」面板 + L4 块 `⚠漂移`；`unknown` → **黄色**「⚠ 漂移未知」面板（不得静默）
- `drift_lines()`：`clean` 返回空；`drifted` 返回文件清单（最多 5 条 + 计数）；`unknown` 返回提示

## 2. 阶段结束自动重审契约（GAP-002 / INC-012）

| 项 | 规定 |
|----|------|
| 触发点 | `se_baseline(任意层)`、`se_descend`、`se_complete_project`；`se_ascend` **不触发**（上升本身就是推翻基线，无需重审旧代码） |
| 执行顺序 | **在所有前置校验之后、状态写入之前**（INC-012）。被拒绝的迁移不得留下 `auto-audit` 记录 |
| `force=true` | 跳过 heal，与跳过其余基线守卫一致 |
| 重审动作 | `gate.ensure()`（text）；命中 `config_error`（无代码可审）时**放行但不写报告、不记日志** |
| 失败语义 | text 不通过 → `ConsistencyGateError`；design_lag → `DesignLagError`（先 ascend 补设计）；转换中止 |
| 通过后 | 刷新 `consistency.code_fingerprint`；若策略要求 LLM 且报告指纹与当前不符 → 结果标 `needs_llm=true` |
| 变更日志 | 仅成功重审时写 `auto-audit` 条目，before/after 记录指纹 |

## 3. LLM 结论必须匹配当前指纹（INC-005）

`llm_status()` 语义收紧：

| 字段 | 定义 |
|------|------|
| `present` | 本轮存在 kind=llm 报告 |
| `matches_current` | 报告的 `code_fingerprint` == 当前代码指纹 **且** 报告的 `design_hash` == 当前设计哈希（v0.15）。报告缺 `design_hash` 时 **fail-closed**（视为不匹配） |
| `satisfied` | `not required` 或 (`present` 且 `matches_current`) |

**三处门控（baseline-strict / descend-L4→L5 / complete）一律以 `matches_current` 为硬前置**：代码在审计后变动过，旧结论不再有效，必须重审。

## 4. Triage 覆盖性约束（INC-009）

- `se_store_triage` 提交的 findings 必须**覆盖该报告的全部 inconsistencies + gaps**
- 缺项 → 返回 `TriageError`，列出缺失 id，**不写入**
- 允许额外条目（例如报告中未列出的新发现），但必须有 classification/confidence
- 理由：部分裁定等于静默丢弃未处理项，比伪造 status 更隐蔽

## 5. 决策状态机（GAP-005）

| decision | 条件 | 门控 |
|----------|------|------|
| `clear` | 报告中没有任何 findings | 放行 |
| `no_llm_report` | 本轮无 LLM 报告 | 阻断（要求先审核） |
| `escalate` | 存在**未裁定**项（classification 缺失或 confidence 缺失），或存在需人工项且 status=open | 阻断 + 列升级项 |
| `auto_fix_pending` | 全部已裁定为 impl_bug/high，但有 open | 阻断 + 列待修项 |
| `auto_fixable` | 全部已裁定，且不需要人工修复（全部 fixed/decided/accepted） | 放行 |
| `resolved` | 全部已裁定为 design_*/ambiguous 且均有 decision（decided/accepted/deferred） | 放行 |

> 修正：原实现把"已裁定为 design_gap"落入 `auto_fixable`，语义相反。现拆出 `resolved`。

## 6. 裁定流程单一化（INC-007）

- **裁定走工具路线**：`se_triage_prompt` 出题 → 调用方（reviewer）作答 → `se_store_triage` 入库
- **删除**"PROMPT v3 追加段"的表述；`PROMPT_TEMPLATE` 保持 v2（缺口清单 + 实现一致性），不要求 classification
- 理由：一次审计与一次裁定是两种判断，混在一个 prompt 里会让 LLM 在"描述问题"时就预先下结论

## 7. 工具清单以代码为准（GAP-004）

- 设计文档的工具总表**由脚本从 `vinw/server.py` 生成**并与实现同步
- 新增测试断言：`len(se_* 工具) == 设计清单条目数`
- 版本历史表补齐缺失行（v0.11、v0.13）

## 8. 版本编号统一（GAP-003）

以 **L3 基线与 changelog 为准**：自 v0.14 起章节号 = 基线号 - 1（v0.14 ↔ 基线 v015）。

历史特例（不回填，仅记录）：descent-11 章节 v0.11 ↔ 基线 v013、descent-12 章节 v0.12 ↔ 基线 v014，
二者差 2（当时按"章节号 = 基线号 - 2"编号）。**规则自 v0.14 起生效**，历史记录保留原样以免伪造。

## 附：v0.13 独立节（原内联于 v0.10）

**required / advisory 二分**与**默认扩展名补 .tsx/.js** 两项内容见前文
「设计侧符号的 required / advisory 二分（v0.13）」小节与 manifest 配置表；
本节仅作版本索引，避免按版本号查找时缺失。

## 已知限制（v0.14 记录）

| 编号 | 限制 | 影响 | 后续 |
|------|------|------|------|
| L-01 | **设计正文不在基线快照内**：`freeze_baseline` 只快照 README，ascend 回滚也只恢复 README | 设计正文（api-design.md 等）在基线后仍可被原地改写而不留版本痕迹；「先改代码后补设计」的顺序不可从数据判定 | 待做：把层内全部文档纳入基线快照，或要求设计正文变更必须先 `se_log_change` |
| L-03 | `heal_drift` 曾不刷新审计基线：`ensure()` 命中 fresh 复用时不写 state，导致漂移永不收敛 | TUI 常红、auto-audit 反复累积 | 已修：新增 `sync_audited_state()` 在 heal 成功后重新锚定指纹 |
| L-02 | `design_synced` 只表示"两者都变了"，不表示先后顺序 | 无法区分"设计先行"与"代码先行后补设计" | 待做：manifest 记录 code_fp/design_fp 的变更时间，或结合 ascent 时间戳判定 |

## 版本历史补记

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.11 | 2026-11-14 | 分层审计契约（策略矩阵/kind 分流/v2 schema/tooling_discrepancy） |
| v0.13 | 2026-11-14 | required/advisory 二分规则、默认扩展名补 .tsx/.js（原内联在 v0.10 章节，现独立成节） |
| v0.14 | 2026-11-14 | 本版：漂移契约、自动重审契约、LLM 指纹前置、triage 覆盖性、决策状态机、裁定单流程、工具清单以代码为准 |

## 9. 设计-实现同步契约（v0.14 补充，回应「代码不应跑在设计前面」）

漂移分五态（与 §1 一致），**不得把"代码改了设计没改"当成正常漂移**：

| state | 条件 | 处置 |
|-------|------|------|
| `design_synced` | 代码与 L3 设计**都**变了 | 允许，但必须重新审计 |
| `design_lag` | 代码变了、L3 设计**未**变 | **拒绝**：先把变更补进设计（走 ascend），再审计 |
| `drifted` | ① 代码变了但**无法判定设计是否变**（无 design_hash）→ reason `code_changed_since_audit_design_unknown`；② **仅设计变、代码未变** → reason `design_changed_since_audit` | 提示"需重新审计"，不臆断为 lag |
| `clean` / `unknown` | 一致 / 指纹不可用 | 见第 1 节 |

判定依据：`layer_states[L4].consistency.design_hash`（审计时记录的 L3 全层哈希）与当前 L3 全层哈希比对；缺失时回退到最近一份 LLM 报告的 `design_hash`。

呈现：`design_lag` 在 TUI 显示红色「🚫 实现先于设计」面板，文案明确"不接受只改代码不改设计"。

---

# v0.15 全阶段审计契约（descent-14 / asc-013）

## 背景（用户裁定 A）

v0.14 只在 **L4→L5** 与 **项目完成前** 校验"审核结论是否匹配当前设计与代码"，导致中间轮次（L5→L6、任意层 baseline）即便工作区已漂移也能推进。用户要求：**任何阶段转换前，只要工作区偏离审计基线，就必须持有针对当前设计与代码的审核结论。**

## 契约

### 判定单元：`StageAudit`

每次阶段转换（`se_baseline` 任意层 / `se_descend` 任意转换 / `se_complete_project`）执行：

1. `heal_drift()`：先按现有规则处理漂移
   - `design_lag` → `DesignLagError`（先 ascend 补设计）
   - `config_error` / `unknown` → 放行（无可审对象）
   - 其余 → 重跑 text 检查；不通过 → `ConsistencyGateError`
2. **新增**：若本次确实发生了漂移（`healed=True`）且 `consistency_policy` 要求 LLM（`text+llm` / `strict`）：
   - `llm_status().satisfied == False` → 抛 `LLMAuditRequiredError`
   - 即：**漂移后的第一次转换必须出示新的审核结论**，不接受"旧结论 + text 重查"过关
3. 无漂移（`clean`）时不做额外要求：现有结论仍然匹配，直接放行

### 执行顺序（v0.15 修订，回应 reviewer6）

`baseline()` 的守卫顺序（v0.15 最终版，与实现逐行对应）：

```
占位符守卫（只读）
  → 【仅 L4 层】strict 策略：LLM 结论校验 + triage 判定（只读）
    → heal_drift（L4 用 log=False）：
         detect_drift 快照
           → design_lag → DesignLagError
             → 无代码文件 → config_error（heal 内部直接返回，不锚定）
               → LLM 结论校验（不满足 → LLMAuditRequiredError）
                 → text 复查（ensure；失败 → ConsistencyGateError，
                               但已写失败报告 + last_failed_*）
                   → 通过才：sync_audited_state() 锚定
  → 【仅 L4 层】第二次 gate.ensure() 校验（此前 heal 已锚定，通常命中 FRESH）；
      若返回 config_error → ConsistencyConfigError（**拒绝**）
      若出现指纹冲突 → ToolingDiscrepancyError / ConsistencyGateError
  → 【仅 L4 层】全部通过后补写 auto-audit
  → 写状态（freeze / descend）
```

**strict 的作用域**：仅在 `layer == L4` 且 `not force` 时执行；L1–L3、L5–L7 的 baseline 不要求 LLM 结论。

**顺序取舍**：strict 校验在 heal 之前，因此「strict 缺结论」会先于「design_lag」报出。
两者都是零状态写入的拒绝，优先级仅影响提示文案，不改变放行结果。

### 「被拒零写入」的准确含义

| 拒绝点 | 是否写报告 | 是否改锚点 | 是否写 auto-audit |
|--------|-----------|-----------|------------------|
| 占位符 / strict / triage | 否 | 否 | 否 |
| heal 内 design_lag / LLM 结论缺失 | 否 | 否 | 否 |
| text 复查不通过 | **是**（失败报告 + `last_failed_*`，作为证据） | 否 | 否 |
| 二次 `ensure` 返回 `config_error`（L4 且无代码文件） | 否 | 否 | 否 → **抛 `ConsistencyConfigError` 拒绝** |
| 二次 `ensure` 的冲突/不一致分支 | 否 | 否 | 否（仅当两次 ensure 之间文件变动，即 TOCTOU 窗口） |

> 即：拒绝**不会移动审计锚点、不会写 auto-audit**；text 复查失败会留一份失败报告作证据。
> 注意 `config_error` 的双重性：`heal_drift` 内部视为"无可审对象"放行，但 L4 的二次 `ensure`
> 会把同样的情形判为配置错误并**拒绝基线**（提示检查 `code_root` / `code_extensions`）。
> heal 与写状态之间仍存在理论上的 TOCTOU 窗口（两次 ensure 之间文件被改动），当前实现依赖
> ensure 的 FRESH 短路，而非结构保证——记录为已知限制。

> 早期实现把第 6 步放在第 4 步之前，导致"被拒一次后重试即通过"的绕过（reviewer6 GAP-001）；`L4` 基线处 `ensure()` 抢在 heal 之前也会同样洗掉漂移（GAP-002），现已在 L4 分支先 heal。

### 漂移基线的取值顺序（v0.15 补充）

`detect_drift` 的审计基线依次尝试：

1. `manifest.layer_states[L4].consistency.code_fingerprint` / `design_hash`
2. 最近一份 LLM 报告的 `code_fingerprint` / `design_hash`
3. 最近一份通过报告的指纹
4. 都没有 → `unknown`（不得等同 clean）

> 回退后若报告缺 `design_hash`，按 §1「设计未知」处理（`drifted`，要求重新审计）。

### 结论复用条件（v0.15 补充）

`se_check_consistency(method="llm")` 仅在下列条件**全部**满足时返回 `reused=true`：

1. `freshness(kind="llm")` 为 `fresh`
2. `llm_status().satisfied` 为真
3. 调用方未传 `ignore_fresh=true`

否则一律返回可执行的审核 prompt。`ignore_fresh` 用于"必须重新审一遍"的场景。

### 锚点写入契约（v0.15 补充）

- 三处写入点（`_record_state` / `record_llm_state` / `sync_audited_state`）**不得用 None 覆盖既有值**：
  报告缺某字段时保留锚点原值
- 读取侧（`detect_drift`）在锚点缺 `design_hash` 时，回退到**锚点所指向的报告**的 `design_hash`；
  仅当两者都缺才按"设计未知"处理
- 理由：历史锚点可能由旧版本写入而缺字段，若不回退，已完成的工程会永久报告 `design_changed_since_audit`

### 失败重审不得锚定（v0.15 补充）

`ensure()` 生成报告后：`overall == passed` 才刷新 `consistency.code_fingerprint/design_hash`；
失败时只写 `last_failed_report/last_failed_overall/last_failed_at`，**不改锚点**——
否则一次失败的重审会把漂移洗白，重试即可绕过全部检查。

### force 与已知限制

- `force=true` **跳过 heal**（含 v0.15 结论要求）；该路径会在 `changelog` 的 baseline 条目以 `[force]` 前缀标注，事后可辨
- 「结论指纹取入库时刻」（GAP-006）：审核 prompt 不含 nonce，若先改代码后补存结论，指纹仍会匹配。**声明式绑定，不可密码学验证**；缓解：先审核再改动，或改动后重审

### 与既有门控的关系

| 门控 | v0.14 | v0.15 |
|------|-------|-------|
| `se_baseline(任意层)` | 仅占位符守卫 + heal | heal + **漂移后强制新结论** |
| `se_descend(任意转换)` | 仅 L4 出口校验 LLM | heal + **漂移后强制新结论** |
| `se_complete_project` | 校验 LLM + triage | 不变（已最强） |

### 未漂移时的成本

`detect_drift` 只做哈希比对（毫秒级），不触发审计、不产生报告 → 正常路径零额外开销。

### 与 `needs_llm` 的关系

`heal_drift` 原返回 `needs_llm=True` 仅作提示；v0.15 起该情形在转换处**直接阻断**（抛错），而不是让调用方自行判断。

## 失败语义

| 异常 | 触发 | hint |
|------|------|------|
| `DesignLagError` | 代码变了、设计未变 | 先 ascend 补设计 |
| `LLMAuditRequiredError` | 漂移已修复但结论过期/缺失 | 用 reviewer 重新审核并 `se_store_consistency_report` |
| `ConsistencyGateError` | text 复查不通过 | 修复不一致后重试 |

## 已知取舍

- **成本**：每次"代码或设计变更后的第一次转换"需要一次独立审核；无变更则无成本
- **不覆盖**：转换之间的连续改动仍由下一次转换拦（无实时守护），这是刻意为此（避免每写一行代码就要求审核）

---

# v0.16 工程发现与自动登记（descent-15 / asc-014）

## 背景（backlog 3）

`se_init_project` 创建工程后只设置进程内 `_active_project`，**不写注册表**；`se_use_project` 同样不登记。
TUI 选择器的数据源是「注册表 + 当前工作目录工程」，因此**跨目录新建的工程在选择器里根本不出现**，
用户会以为工程丢了（磁盘完好，`se_get_project` 正常）。

## 契约

### 自动登记（A 方案，用户裁决）

| 触发 | 行为 |
|------|------|
| `se_init_project` 成功创建工程 | **自动 `registry.add()`**，返回体新增 `registered: true` |
| `se_init_project` 接管已有工程（adopted） | 同样自动登记（幂等） |
| `se_use_project` 成功解析为工程 | 自动登记（兜底：覆盖未通过 init 进入场景的工程） |
| 显式 `register=false` | 跳过自动登记，用于临时/一次性工程 |
| CLI `vinw init` | 同样自动登记；`--no-register` 可跳过（与 MCP 口径一致） |

幂等保证：`registry.add()` 对同一路径重复调用不新增条目（已有契约）。

### 返回字段

`se_init_project` / `se_use_project` / `vinw init` 成功时追加：

| 字段 | 含义 |
|------|------|
| `registered` | 是否登记成功 |
| `name` | **登记后的可寻址名**（同名冲突时会被改名为 `<name>-2`，须以本字段为准） |
| `warning` | 登记失败或被改名时的说明 |
| `registration_skipped` | `register=false` 时为 true |

> `se_use_project` 的补登记同样返回上述字段：受限环境下若登记失败，调用方可据 `warning` 判断"已激活但不能按名寻址"。

### 异常边界

只容忍**注册表层故障**（`OSError` / `sqlite3.Error` / `ValueError`）并降级为 `warning`；
`TypeError`、`AttributeError` 等编程错误必须向上抛出，否则会被伪装成环境故障。

### 测试隔离（v0.16 追加）

自动登记把"测试会写真实注册表"变成现实风险：`tests/conftest.py` 提供 **autouse fixture**，
把 `VINW_HOME` 指向临时目录并重置 `_registry` / `_active_project` 单例。
否则每跑一次测试都会在开发者 `~/.vinw/registry.db` 里累积 `/pytest-of-*` 幽灵工程
（本轮实测累积 23 条，已用 `prune` 清除）。

### 不改变的行为

- `se_list_projects` 仍只列注册表条目（不做目录扫描，避免慢盘开销）
- 手工 `vinw project add` 与 `se_register_project` 仍是显式入口
- 注册表损坏/不可写时：**工程创建仍成功**，仅在返回体给出 `warning`（不因登记失败回滚工程）

### 错误处理

登记失败不得让 `se_init_project` 失败——工程已落盘，回滚会让用户丢失工作区。
返回：`{project_id, layers, current_layer, current_descent, registered: false, warning: "..."}`

## 影响

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 在别的目录新建工程 → 打开 TUI 按 p | 看不到 | 看得到 |
| 用 `se_use_project` 激活未登记工程 | 后续按名称寻址失败 | 自动登记后可按名称寻址 |

## 已知取舍

- 自动登记会产生"创建即登记"的副作用；用户若想要临时工程，需显式 `register=false`
- 不实现「扫描发现未登记工程」（B 方案）：需要遍历目录，慢盘成本高，且与"注册表即事实源"的设计冲突

---

# v0.17 澄清选项与进程防护（descent-16 / asc-015）

## 〇、R31 定位修正（用户澄清）：LLM 驱动的需求对齐机制

R31 不是孤立的问答工具，而是**"发现假设 → 显性化 → 用户对齐 → 消除偏离"的闭环**，
结合 LLM 能力贯穿三个环节：

1. **发现**：LLM 审计/实现过程中识别歧义点、隐含假设、与用户已有设计/需求的潜在偏离
   （复用 triage 的 `ambiguous` 分类作为发现入口之一）
2. **显性化**：每个澄清请求必须携带 `assumption`（当前理解/默认假设）与 `deviation`
   （假设错误时会偏离什么）——用户不是在回答问题，而是在**纠正或确认 agent 的心智模型**
3. **对齐闭环**：裁决记录 `assumption → confirmed/corrected`；changelog 写 alignment 条目；
   同一主题反复出现歧义时升级为"设计表述缺陷"（该改文档而不是反复问）

### 发起门槛（重要边界，防止过度打扰）

**只在模糊/歧义时发起澄清；高置信度/无歧义时禁止打扰用户。** 具体：

| 情形 | 行为 |
|------|------|
| 唯一合理解读、或置信度高的决策 | **自主执行**，不发起澄清（可写入 changelog 留痕） |
| ≥2 种合理解读且影响产物方向 | 发起澄清（LLM 生成选项与参考分析） |
| 与已有设计/需求文本存在表面冲突、或实现约束可能迫使你背离初衷 | 发起澄清 |
| 影响微小且可逆的执行细节 | 自主执行 |

- 工具层约束：`se_request_clarification` 要求 `uncertainty` 字段（为什么不确定：多解/冲突/约束），
  填写不出 uncertainty 的请求应被发起方拒绝生成——这是制度化的自检
- LLM 职责：审计/实现时给每个决策标注置信度；**低置信 ambiguous 才走澄清**，高置信走自主+留痕
- 参考选项与参考分析（difference/impact）由 **LLM 生成**，不是让用户做填空题

## 一、R31：带参考选项的澄清请求

### 选项结构扩展（兼容性红线）

`se_require_confirmation` 的 `options` 参数向后兼容：仍接受 `["approve","reject","modify"]` 字符串数组；
新增支持对象数组，每项：

```json
{"id": "opt-perf", "label": "性能优先", "description": "接受宏内核复杂度", "impact": "可读性下降，1024³ 预计 +40%"}
```

- `id`：稳定标识（resolution 用）
- `label`：短标签（TUI 按钮文字）
- `description`：参考方向说明（可选）
- `impact`：取舍影响（可选）

### 新工具：`se_request_clarification`

```
se_request_clarification(
  question: str,            # 歧义点描述（必填）
  layer: str,               # 所在层级（必填，如 "L3-方案细化"）
  assumption: str = "",     # 当前理解/默认假设（对齐核心：用户确认或纠正的对象）
  deviation: str = "",      # 若假设错误会偏离什么（用户意图/已有设计）
  context: str = "",        # 背景/为什么需要确认
  options: str = "[]",      # 参考选项 JSON 数组（≥2，结构如上；自动追加 {"id":"other","label":"其他（请说明）"}）
  blocking: bool = false,   # 是否阻塞当前层推进（默认否）
  recommendation: str = ""  # 发起方的推荐选项 id 与理由（可选）
) -> {confirmation_id, status: "pending"}

# 从审计歧义一键发起（LLM 驱动入口）：
se_request_clarification_from_finding(finding_id: str, layer: str, ...) -> {confirmation_id}
# 将 triage 中 classification=ambiguous 的发现的 difference/analysis 预填为
# assumption/deviation，agent 只需补 question 与 options。
```

- item_type 固定为 `"clarification"`，写入 manifest.pending_confirmations（复用既有存储、purge、changelog 语义）
- blocking=true 时参与既有一致性门控的 blocking_pending 统计
- **对齐语义**：resolution 为选项 id 或 modify 文本时，changelog 写 `alignment` 条目：
  `{question, assumption, resolution, corrected: bool}`——corrected=true 表示用户纠正了假设
- 同一 `layer+question主题`（按 id 前缀聚类）第 3 次发起时，工具返回 warning：
  「该主题已反复澄清 N 次，建议改为修订设计文档」

### 裁决扩展：`se_resolve_confirmation`

`resolution` 允许直接填**选项 id**（如 `"opt-perf"`）；选择选项时 `feedback` 可选（补充说明），
选择 `"other"` 时 `feedback` 必填。裁决记录写入 changelog：`{question, chosen_option, feedback}`。

### TUI 呈现

确认面板中 clarification 类型的问题展开显示：**assumption（当前假设，高亮）**、deviation（偏离风险）、
context、各选项的 label+description+impact、推荐项标记（★推荐）。
键盘：数字键选择选项 / a拒绝 / m修改。选中后写入 resolution。

## 一之二、与 LLM 审计的衔接

- triage 输出中 `classification=ambiguous` 的发现，其 escalation 呈现时附带提示
  「可转为澄清请求」；转换后该 finding 标记 `clarification_id`，裁定决策引用用户答案
- LLM 审核 prompt（PROMPT_TEMPLATE）不变——ambiguous 归类已是 v2 语义；衔接发生在工具层

## 二、R30：进程陈旧防护

### server_version（AC1）

- `vinw/__init__.py` 暴露 `__commit__`：构建/启动时取 `git rev-parse HEAD`（失败则为 `"unknown"`）
- `se_get_project` 响应与 server 启动日志均带 `server_version`
- TUI（AC2）：启动时读仓库 HEAD 与 `se_get_project.server_version` 对比，不符则 header 显示
  `⚠ server 代码陈旧（启动于旧版本）——请重启 MCP server`

### design_hash_algo（AC4）

- 报告 frontmatter 与 manifest consistency 均写 `design_hash_algo: "layer-v1"`（当前算法）
- `freshness` / `llm_matches_current`：报告缺该字段或值不符 → 视为 stale（fail-closed，同 design_hash 缺失语义）
- 算法升级时递增版本号，旧报告自然失效

## 三、R32 边界

decision_bias 本轮**不进设计**（L2 调研已定结论：混合形态、问卷 v1、规则映射）；实现另行立项。

## 版本历史补记

| 版本 | 下降轮 | 内容 |
|------|--------|------|
| v0.17 | descent-16 | 澄清选项结构、se_request_clarification、server_version、design_hash_algo |
