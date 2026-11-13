---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "implementation"
updated_at: "2026-11-13T10:02:19.675591"
---

# 实现笔记

## 关键代码决策

## 与设计文档的映射

| 设计文档段落 | 代码位置 | 实现状态 |
|-------------|---------|---------|
| — | — | — |

## 待解决问题

- [ ] —

## descent-2 实现记录（asc-001，2026-11-13）

### 变更内容
1. **自举加载**（server.py）：模块导入时 `_try_load_bootstrap_project()` 探测 `cwd/vinw-design/.vinw/manifest.md` → `cwd/.vinw/manifest.md`；`se_init_project` 对已初始化目录返回 `adopted=true`
2. **一致性检查代码定位**（consistency_llm.py）：`_resolve_code_root()` 读取 manifest `code_root`；`_collect_code_files()` 支持文件/目录混合，排除 `.venv`/`build`/`node_modules`/`__pycache__`/`.git`
3. **.vinw 更名**（全仓）：`Project.se_dir` → `Project.vinw_dir`，路径字面量 `.se` → `.vinw`，vinw-design 状态目录已移动

### 验证
- `se_check_consistency`(text, scope=vinw/)：20/20 符号匹配，overall=passed → report-c88f12f4.md
- `pytest tests/`：45/45 通过（新增 test_bootstrap.py 8 例 + 一致性定位 2 例）
- MCP 自举实测：重启后自动加载 vinw-self-design（当前层 L3→下降链已推进）

## descent-3 实现记录（asc-002，2026-11-13）

将 descent-2 终验后的三项热修正式纳入 L4 基线（变更日志 chg-032/033/034）：

1. **TUI 渲染崩溃修复**（tui/app.py）：Columns + Text 非法相加 → rich Group 组合（chg-032）
2. **待办轮次追踪**（server.py + store/project.py）：se_update_todo 写入 todo_descent frontmatter；get_todos 优先读取写入轮次（chg-033）
3. **TUI 可滚动 + 刷新容错**（tui/app.py）：面板 overflow-y: scroll 常驻滚动条；refresh_ui 异常兜底保留上次渲染（chg-034）

验证：52/52 测试通过（新增 test_tui.py 4 例 + todo 追踪 3 例）

## descent-4 实现记录（asc-003，2026-11-13）

1. **se_complete_project**（server.py）：终验完成态迁移。前置校验（当前层=L7、L1-L6 全 baselined、无未解决 blocking 门控）→ L7 README completed + manifest layer_states/completed_at + changelog；前置不满足返回结构化 error
2. **TUI completed 渲染**（tui/app.py）：层状态图新增 🏁 bold green 分支；滚动条修复（overflow-y: scroll）随本次重装正式生效
3. 测试 +3（完成成功/非 L7 拒绝/阻塞门控拒绝且状态不变），55/55 通过

## descent-5 实现记录（asc-004，2026-11-13）

**TUI 面板结构性重做**（chg-20261113-163132-055）：
1. compose 改为 `VerticalScroll` 容器（top/mid/bottom 40/35/25%）包裹内层 `Static#*-content`，内层 `height: auto`
2. 根因：固定高度 `Static` 渲染 rich renderable 时转成按视口裁剪的 `Visual`，`virtual_size` 恒等于容器高，`overflow-y` 永远无滚动内容
3. 待办表格重做：`expand=True`、Layer 列 min/max 宽度 + fold、状态独立列（✅/⏳/🔒/🔓）、内容列 ratio=1；标题改为「N/M 已完成, K 待确认」
4. 移除原有 `Horizontal`/`Vertical` 未使用导入

验证：`#mid-panel max_scroll_y: 39`（实测 33 todo + 1 pending），三个面板滚动条常驻；56/56 测试通过。

## descent-6 实现记录（asc-005，2026-11-13）

三项结构性修复（L3 v0.6 设计）：

1. **待办生命周期**（store/project.py）：新增 `extract_todo_section()` / `replace_todo_section()` / `has_placeholder_todo()`；`rollback_to_baseline` 恢复基线正文后回填**现场待办段**与 `todo_descent`，回滚不再倒带工作进度
2. **基线占位符守卫**（workflow/state_machine.py + server.py）：`se_baseline(force=False)` 在待办仍为 `- [ ] 初始化本层工作` 时拒绝并返回 error+hint；`force=True` 显式跳过；`se_complete_project` 前置条件追加占位符检查
3. **门控清理**（workflow/state_machine.py + server.py）：新增 `se_purge_confirmations(before_descent=0, resolution="superseded")`；`se_complete_project` 完成前自动结转较早轮次的**非阻塞**门控并回报 `purged_confirmations`，blocking 门控仍阻断

测试：新增 tests/test_todo_lifecycle.py 15 例；全量 71/71 通过（含因守卫生效而适配的旧用例：机制类测试显式 force=True）

## descent-7 实现记录（asc-006，多项目跟踪管理）

### 新增模块
- `vinw/store/registry.py`：`ProjectRegistry`（JSON 单文件 + 原子写 + 探测式状态）
  - `load/save`（tmp + os.replace；损坏备份为 `.bak-<ts>` 后重建空表，不丢文件）
  - `add/remove/get/list/touch/prune/resolve/describe`
  - `resolve()` 顺序：存在的路径 → 注册名/路径 → `ProjectNotFound`
  - 失效条目只标记 `status: missing` + `missing_since`，`prune` 默认 dry-run
- `vinw/tui/selector.py`：`ProjectSelector` 模态（注册工程 + 当前目录工程，↑↓/Enter/Esc）

### 改造
- `vinw/server.py`：21 个 `se_*` 工具全部支持可选 `project` 参数（AST 精确改写签名）；`_project_or_error()` 统一解析，非法值返回结构化 error + `available_projects`；新增 5 个注册表工具 `se_register_project/se_list_projects/se_remove_project/se_prune_projects/se_use_project`
- `vinw/tui/app.py`：header 增加工作目录栏（`工作目录: <cwd>` + `当前工程: <name> @ <path>`）；无参启动自动弹选择器；`p` 切换、`r` 刷新、`q` 退出；空工程时显示引导面板
- `vinw/__main__.py`：`vinw project add/list/remove/prune`；`vinw tui <path|name>` 支持注册名

### 验证
- 测试 101/101 通过（新增 test_registry.py 26 例、TUI 多项目 4 例）
- 实测：`se_list_projects` 返回注册表；`se_get_project(project="vinw-self-design")` 正常解析；CLI `project add/list/prune` 正常
- 兼容红线：`project=None` 时全部沿用原自举/单例逻辑（回归测试覆盖）

## descent-8 实现记录（asc-007：注册表改 SQLite）

### 控制面 / 数据面分层落地
- **控制面**：`vinw/store/registry.py` 重写为 SQLite 实现（`$VINW_HOME/registry.db`）
  - `projects` 表：path 主键、name 唯一、state(active/dormant)、added/last_accessed/last_seen_ok/missing_since
  - `project_events` 表：register/remove/activate/deactivate/missing/recover/import 全量留痕（含索引 path,id DESC）
  - 连接参数：`journal_mode=WAL`、`busy_timeout=5000`、`foreign_keys=ON`；短连接 + 事务
  - `PRAGMA user_version=2` 控制 schema 版本
- **数据面**：`<工程>/.vinw/*.md` 完全未改动

### 三项核心改进
1. **消除写放大**：`touch()` 由「整表读+整表重写」改为单行 `UPDATE`
2. **并发安全**：WAL + busy_timeout 替代原先「写前重读 + 原子替换」，并新增并发写测试（双连接并发 add 均存活）
3. **intent/observation 分离**：`state`（用户声明）与 `missing_since`（系统观测）独立；默认只探测 active，dormant 用缓存并标 `probed: false`

### 迁移与容错
- 首次打开若发现遗留 `registry.json`：逐条导入 + 写 `import` 事件 + 原文件重命名为 `registry.json.migrated-<ts>`（实测真实注册表迁移成功）
- 库文件损坏：`_quarantine_if_corrupt()` 将其重命名为 `registry.db.corrupt-<ts>` 后重建（保留文件，不静默删除）

### 工具与 CLI 增量
- MCP 新增：`se_set_project_state`、`se_project_history`、`se_export_projects`（共 30 个 se_* 工具）
- CLI 新增：`vinw project activate|deactivate|history|export`

### 修复的自身缺陷
`list()` 探测分支漏 `entries.append(entry)`，导致 probe 路径返回空列表（开发期自查发现并修复，测试覆盖）
