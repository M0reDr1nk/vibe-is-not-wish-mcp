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

## descent-9 实现记录（asc-008：一致性门控）

### 新增
- `vinw/workflow/consistency_gate.py`：`ConsistencyGate`
  - `freshness()` 四态判定：`fresh` / `stale_files` / `stale_design` / `missing`
  - `ensure()`：非 fresh 时自动跑 text 检查并落盘报告（自动兜底），fresh 时零成本复用
  - `latest_passing(descent)`：按轮次筛选通过报告
  - `_record_state()`：把 `{report_id, overall, descent, checked_at, code_fingerprint}` 写入 `manifest.layer_states[L4].consistency`
- `consistency_llm.py`：`file_hashes()` / `layer_design_hash()` / `aggregate_fingerprint()`；`store_report()` 增加 `descent/scope/design_hash/file_hashes/code_fingerprint` 元数据

### 三处门控（必然触发）
| 位置 | 行为 |
|------|------|
| `WorkflowEngine.baseline("L4-编码实现")` | 自动 ensure；未通过则拒绝（`force` 可跳过） |
| `WorkflowEngine.descend(L4→L5)` | 同上，防绕过基线门控 |
| `se_complete_project` | 校验本轮存在 passed 报告 |

### 增量复用（避免重复检查）
- `se_check_consistency(method="llm")` 先判新鲜度：fresh → 返回 `{reused: true, report_id, overall}`，不构造 prompt、不消耗审计
- text 检查成本毫秒级且符号存在性跨文件，故始终全量扫描（按文件增量会误报缺失）
- 实测：`ensure` 首次 `missing` 跑检查，二次 `fresh` 直接复用；MCP 侧同样返回 `reused: true`

### 非阻塞门控呈现改进
- `se_get_project` 拆分 `blocking_pending` / `pending_review`（含 `age_days`）并输出 `consistency` 状态
- `se_get_next_steps` 新增 `awaiting_review`（无待办时也列出）
- `se_complete_project` 结果回报 `pending_review`
- TUI 待办面板分两组：`🔒 阻塞（会卡流程）` / `🔓 待你审阅（不卡流程）`，标题显示双计数，存在阻塞门控时边框转红
- `se_require_confirmation`：`requirement-decomposition` / `interface-design` 默认阻塞，其余默认非阻塞

### 开发期自查发现并修复
1. 报告 frontmatter 手拼 YAML 导致解析失败（`file_hashes` 内嵌引号）→ 改用 `frontmatter.dumps(Post(...))` 由 yaml 序列化
2. 设计指纹只覆盖 `design-doc.md`，而检查读的是 `api-design.md` → 改为整层 `*.md` 聚合哈希（否则改接口设计不会使缓存失效，属漏检）

## descent-11 实现记录（asc-010：分层审计契约）

### 新增/改造
- `consistency_llm.py`：**PROMPT_TEMPLATE v2** —— 分 A 缺口清单 / B 实现一致性（逻辑/数据结构/接口/约束），强制 `design_ref`+`code_ref` 证据，输出 schema 增加 `gaps`
- `consistency_llm.store_report()`：新增 `kind`(text/llm)、`policy`、`auditor`、`auditor_model`；llm 类报告写 `llm_verdict`、`gaps_count`
- `consistency_gate.py`：新增 `policy()` / `llm_status()` / `discrepancy()` / `readiness()` / `record_llm_state()`；`latest_passing(descent, kind)`
- `state_machine.py`：新增 `LLMAuditRequiredError` / `ToolingDiscrepancyError`；L4→L5 下降在 text 通过后按策略校验 LLM 结论与冲突
- `server.py`：`se_store_consistency_report` 增加 `auditor`/`auditor_model`，自动标记 kind=llm 并回写 manifest；`se_complete_project` 按策略校验 LLM；`_consistency_state()` 输出 `policy`/`needs_llm`/`llm_verdict`

### 默认策略
`consistency_policy = "text+llm"`：基线只需 text（快），**L4→L5 与完成前强制 LLM 语义审核**。

### 修复的自身缺陷
1. 变量遮蔽：`se_store_consistency_report` 内 `auditor` 形参被同名对象覆盖，导致 YAML 无法序列化对象（测试抓到）
2. 正则跨行吞符号（descent-10 遗留，本轮一并修复）

### 验证
测试 156/156 通过（新增 test_audit_policy.py 14 例、test_symbols.py 14 例）

### descent-11 追加：符号提取语义修正（关键）

实测本项目自身时出现 73 项"缺失"，全部是**配置键 / 枚举值 / 第三方类名 / prose 提及**，并非 API。据此把设计侧符号分为两类：

| 类别 | 判定 | 门控作用 |
|------|------|---------|
| **required**（必须存在） | API 表（表头含 接口/工具/函数/命令/API）的首列标识符、单列表格标识符、`foo(` 调用形式、代码围栏中的 `def/fn/func/class` 签名 | 缺失 → **阻塞** |
| **advisory**（仅供参考） | 其他反引号标识符（配置键、状态机取值、字段名、prose） | 缺失 → 仅列入 `advisory_missing`，不阻塞 |

同时修正噪声：SQL/JSON 围栏不计入符号；版本号（`v0`）、内置函数与标准库（`sorted/rglob/sha256/...`）、模块与表名（`vinw/project_events`）加入过滤。

效果：本项目 required 50 / advisory 76，阻塞项从 73 降至 0；并借此发现 2 处真实设计漂移（`resolve_project`→`resolve`、已删除的 `load/save` 仍留在 API 表）。

## descent-12 实现记录（asc-011：审计分级裁定）

### 新增模块 `vinw/workflow/triage.py`
- `normalize_finding()`：规范 classification（impl_bug/design_bug/design_gap/ambiguous）、confidence（high/medium/low）、difference/analysis/recommendation/impact、status
- `requires_human()`：仅 `impl_bug + high` 可自动处置，其余一律需人工
- `AuditTriage`：`store()`（裁定结论附着到最新 LLM 报告）、`findings()`、`decision()`、`record_decision()`、`escalations()`
- 门控决策四态：`clear` / `auto_fixable` / `auto_fix_pending` / `escalate`

### 新工具（4 个，共 34 个 se_* 工具）
| 工具 | 作用 |
|------|------|
| `se_triage_prompt` | 给出裁定指令 + 待裁定 findings |
| `se_store_triage` | 写入 classification/confidence/recommendation |
| `se_get_escalations` | 列出待人工裁决项（差异点/分析/推荐/影响面） |
| `se_record_triage_decision` | 记录裁决：fix_impl / fix_design / accept_as_is / defer |

### 门控接入
- `descend(L4→L5)`、`se_baseline(L4)`（strict）、`se_complete_project` 均先查 `triage.decision()`
- `escalate` → `AuditEscalationError`（附 escalations 列表）
- `auto_fix_pending` → 阻断并提示修正后 `se_record_triage_decision(fix_impl)`

### 修正的门控缺陷（reviewer 本轮指出）
1. **INC-001** strict 在基线处为空策略 → 已接线
2. **INC-003** tooling_discrepancy 分支不可达 → 判定提前到 text 失败分支
3. **INC-009** 空扫描被误落盘为 unknown 报告 → 改为返回 `config_error` 且不落盘
4. **INC-002/GAP-005** 报告缺 `files_scanned`/`extensions`/`code_symbols_count` → 已写入 frontmatter
5. **INC-006** `.c` 把声明当实现 → 移除声明正则（声明归头文件）
6. **GAP-001** `tooling_discrepancy` 不落盘 → 新增 `mark_discrepancy()`
7. **GAP-002** `consistency_auditor` 配置未生效 → 作为工具默认值读取
8. **INC-004** 证据缺行号 → 新增 `extract_code_symbols_with_lines()`

### LLM 报告结论与门控的关系（重要语义修正）
`overall=warning` 的 LLM 报告**不再直接拒绝**：它代表"审核已完成且发现问题"，由裁定环节决定放行/升级。仅"缺失 LLM 报告"才抛 `LLMAuditRequiredError`。

## descent-13 实现记录（asc-012：审计契约补全）

### 按 v0.14 设计落实的改动

| 设计条目 | 实现 |
|---|---|
| 漂移四态 + changed 列表 | `drift.py` 输出 `state` ∈ clean/drifted/design_lag/design_synced/unknown，`changed` 为 `added|removed|modified:<路径>`；`unknown` 在 TUI 显示黄牌，不再等同 clean |
| heal 契约 | `heal_drift` 移到 baseline/descend 的**前置校验之后**；`force=true` 跳过；`config_error` 放行且不写报告；仅成功重审写 `auto-audit` |
| LLM 指纹前置 | `llm_status.satisfied = not required or (present and matches_current)`；三处门控改用 satisfied，并在错误信息区分"未提供/报告针对旧代码/结论未过" |
| triage 覆盖性 | `store()` 在写入前比对报告全部 inconsistencies+gaps，缺项抛 `TriageError` 且不落盘 |
| 决策五态 | 新增 `resolved`（全部已裁定且含 design_*），未裁定项归入 `escalate` 并在输出列 `untriaged` |
| 裁定单流程 | 删除 PROMPT v3 表述，裁定只走 `se_triage_prompt` → `se_store_triage` |
| 工具清单 | 设计总表由 `server.py` 生成（34 项），`test_tool_catalog.py` 断言两侧一致 |
| 设计-实现同步 | 新增第 9 节契约；`consistency.design_hash` 入库供漂移判定 |

### 开发期发现的自身缺陷
1. `llm_status.satisfied` 初版把 `overall=="passed"` 写进条件，与设计第 3 节不符，导致 warning 结论被误判为"未提供审核" → 按设计修正
2. `drift` 判定 design_hash 时依赖"当前轮 LLM 报告"，跨轮时取不到会误判 design_lag → 改为 manifest 优先、报告回退、缺失降级为 drifted
3. TUI 内局部的 `from ..workflow.drift import drift_lines` 造成整函数作用域遮蔽，页面渲染报错 → 提为模块级导入

### descent-13 追加：状态机同步（审查后修复）

| 缺陷 | 修复 |
|------|------|
| manifest 与 README status 各自为政（实测 6/7 层分歧） | manifest 为唯一状态机，README 为镜像；`_sync_layer_status()` 在所有转移点同步，`sync_all_layer_readmes()` 修历史分歧 |
| `descend` 未清 `needs_redo`/`superseded_by` | 进入层时清除 |
| `baseline` 未清 supersede 标记 | 冻结时清除 |
| `layer_design_hash` 含 README → 同步状态即"设计变了" | 设计哈希排除 README.md |
| `get_todos` 按 README 过滤 superseded（死代码） | 改按 manifest 状态 |
| `repair_ascend_state` 误把当前层标 superseded | 保留 current 为 in_progress |

不变量测试：恰好一层 in_progress 且 == current_layer；completed 仅 L7；superseded 必带 superseded_by；重做清除残留标记。

### descent-13 追加：reviewer4 修复

| 缺陷 | 修复 |
|------|------|
| descend 离开未基线层留下两层 in_progress | 源层复位为 `pending` 并记 `abandoned_at`，README 同步 |
| repair 只写 manifest、残留 supersede 标记、未知 ascent 静默回退 | 镜像 README + 清全部标记 + 未知 id 抛错 |
| triage 覆盖集用 anon-N 与 findings 的 INC/GAP 不一致 | 统一 `finding_id()` 归一化函数 |
| complete 的 heal 早于一致性/triage 校验 | 守卫全部前置，heal 最后执行且日志延后到全部通过 |
| README 只镜像 status，基线版本不更新 | `_sync_layer_status(extra=...)` 同步 baseline_version/baselined_at；`sync_all_layer_readmes` 修历史 |
| drift unknown 分支缺 needs_reaudit/audited_report | 统一 `_result()` 构造，所有路径键集一致 |
| se_baseline 未处理 DesignLagError（裸异常） | 映射为结构化 error + hint + drift 快照 |

## descent-14 实现记录（asc-013：全阶段审计契约 v0.15）

### 改动
- `heal_drift`：漂移修复成功后，若策略要求 LLM（`text+llm`/`strict`）且 `llm_status().satisfied == False`，直接抛 `LLMAuditRequiredError`
  - 覆盖全部阶段转换：`se_baseline(任意层)`、`se_descend(任意转换)`、`se_complete_project`
  - 无漂移（clean）时不触发，正常路径零额外成本（仅一次哈希比对）
- `se_descend` 补充该异常的结构化映射（error + hint + drift + consistency 快照）

### 语义变化（重要）
| 变更前 | 变更后 |
|--------|--------|
| 漂移由 text 重查"洗白"后即可转换 | 漂移后的**第一次转换**必须出示匹配当前设计与代码的审核结论 |
| 仅 L4→L5 与终验校验 LLM | 任意阶段的 baseline/descend 均校验 |
| `heal_drift` 返回 `needs_llm` 提示 | 直接阻断，不再依赖调用方自觉 |

### 验证
- 275/275 测试通过（含：漂移后无新结论 → 阻断；有新结论 → 放行；代码+设计同改 → 需重审；strict/占位符拒绝零写入）
- 真实工程实测：`design_synced` + 无匹配结论时，`descend L5` 与 `descend L6` 均被拒绝

### descent-14 追加：reviewer7 修复

| 缺陷 | 修复 |
|------|------|
| ensure() 失败仍锚定指纹 → 重试绕过 | 仅在 `overall == passed` 时 `_record_state`；失败只写 `last_failed_report/overall/at` |
| L4 基线先 heal 后守卫 → 被拒迁移仍留痕 | **两次修复才完整**：reviewer8 指出日志延迟但状态已锚定；reviewer9 指出 strict/triage 路径同样。现把占位符守卫与 strict/triage 只读校验全部前移到 heal 之前：拒绝时**不改锚点、不写 auto-audit**；text 复查失败会留一份失败报告作证据（`last_failed_*`）。heal 与写状态之间仍有理论 TOCTOU 窗口，已记录为已知限制 |
| force 基线无可辨识痕迹 | reason 加 `[force]` 前缀 |
| 漂移基线回退/结论复用规则未进设计 | v0.15 补三节：回退顺序、复用三条件、失败不锚定 |
| design_lag 与 config_error 判定顺序与文档不符 | 文档改为 design_lag 优先，并说明 hint |

## descent-17 实现：澄清 harness（v0.18 / R34）

### 改动

| 组件 | 内容 |
|------|------|
| `se_request_clarification` | 新增 `impact`/`reversibility`；`blocking` 改为可选（None → 自动推导 `high && irreversible`）；同主题未裁决达 2 条 → 第 3 条强制阻塞并标 `escalated` |
| assumption-taken 留痕 | 非阻塞时写 changelog（问题/假设/**偏离**/影响/可逆/复查点），分隔符用中文分号避免破坏 markdown 表格 |
| `se_clarification_brief`（新） | 一次性汇总 blocking/queued/assumptions_taken；**从 manifest 结构化读取**（不解析 changelog） |
| 引擎门控 | `baseline`/`descend` 新增阻塞澄清守卫（`_assert_no_blocking_clarifications`），与 complete 一致；TUI/MCP 共用 |
| 层转换返回体 | 注入 `pending_clarifications: {blocking, queued}` |

### 评审驱动的修正（reviewer18，11 项）

| 发现 | 修正 |
|------|------|
| brief 返回 changelog 原始行、每条重复两次（critical） | 改读 manifest 记录，按 descent 过滤、去重 |
| AC4 承诺 blocking 阻断 baseline/descend，实际只有 complete 阻断（critical） | 引擎层新增守卫，AC4 字面成立 |
| `summary.assumptions` 与数组长度不一致 | 条目计数 |
| 队列升级 warning 被 repeat_warning 覆盖 | 合并为 `/` 连接 |
| 显式 blocking 与队列升级优先级未定义 | 设计写明 auto < explicit < escalation |
| README 仍写 38 工具 | 改 39 并补 3 个澄清工具 |
| from_finding 不透传分级 | 已透传，blocking 留空以触发自动推导 |

### 测试

316/316（+7：真值表、非法值、显式覆盖、brief 结构、门控集成、非阻塞不阻断、转换计数）

## descent-18 实现：可见性与状态可信度（v0.19）

| 改动 | 内容 | 来源 |
|------|------|------|
| 工程可见性 | `_project_or_error` 解析成功后按工程根登记（幂等，best-effort） | 用户报 gemm 在 TUI 不可见 |
| 状态可信度 | `_invalidate_above`：下层重新基线 → 上层依据失效（superseded + needs_redo + changelog）；`current_layer` 保留 `in_progress` 并置 needs_redo，返回 `current_layer_reset` | 用户问"下层变更是否触发上层检查"（原答案：没有） |
| 完成戳 | L7 离开 completed 时清除 manifest/层内 `completed_at` | reviewer19 INC-008 |
| 性能 | `se_get_project` 只算一次 `detect_drift`（5.6s → 1.8s） | reviewer19 GAP-005 |
| TUI | 三栏：单一问题块（按优先级）、本轮/历史待办分离、底栏结构化变更 + 下一步；`superseded` 改黄（红只留问题）；澄清就地裁决 | 用户三次反馈 |
| 清理 | 删除 `_refresh_ui` 死代码、`se_use_project` 重复登记、问题块重复文案 | reviewer19 |

评审：reviewer19 共 17 项（9 impl_bug / 5 design_gap / 3 design_bug），
15 项已修复、2 项记录为已知取舍（写侧完成态守卫、三处谓词抽公共）。
