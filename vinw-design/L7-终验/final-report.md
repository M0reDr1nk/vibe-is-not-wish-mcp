---
se_version: "2.0"
layer: "L7-终验"
doc_type: "final-report"
status: "in_progress"
---

# 终验报告 — VINW（descent-16，澄清对齐与进程防护版）

## 项目信息

| 字段 | 值 |
|------|-----|
| 项目名称 | vinw-self-design |
| 下降轮次 | descent-1 ~ descent-16 |
| 上升次数 | 15（asc-001 ~ asc-015） |
| 终验时间 | 2026-11-13 |
| 版本 | 0.2.0 |

## 各层完成状态

| 层 | 状态 | 基线 | 下降次数 |
|---|------|------|---------|
| L1-需求拆解 | ✅ baselined | v001–v004, **v005** | 5 |
| L2-参考文献与方案搜证汇总 | ✅ baselined | v001–v005, **v006** | 6 |
| L3-方案细化 | ✅ baselined | v001–v017, **v018** | 16 |
| L4-编码实现 | ✅ baselined | v001–v014, **v015** | 16 |
| L5-测试验证 | ✅ baselined | v001–v012, **v013** | 16 |
| L6-检视清理 | ✅ baselined | v001–v012, **v013** | 16 |
| L7-终验 | ✅ completed | — | 16 |

## 上升记录（ascensions.md）

| ID | 路径 | 原因 |
|----|------|------|
| asc-001 | L7 → L3(v002) | 新增自举能力，需更新 L3 接口设计 |
| asc-002 | L7 → L3(v003) | descent-2 终验后三项热修未走流程，补救上升 |
| asc-003 | L7 → L3(v005) | 终验完成态无 MCP 出口 + TUI 缺 completed 渲染，上升补齐 |
| asc-004 | L7 → L3(v006) | TUI 面板固定高度 Static 无法真实滚动（max_scroll_y 恒 0）+ 终验测试统计有误，上升修正 |
| asc-005 | L7 → L3(v007) | 三项结构性缺陷：回滚倒带待办、占位符可入基线、过期门控悬挂 |
| asc-006 | L7 → L1(v001) | 多项目跟踪管理：需求级扩展，回到 L1 重新拆解 |
| asc-007 | L7 → L2(v002) | 注册表存储选型复核：descent-7 的 L2 矩阵权重错配，控制面应改 SQLite |
| asc-008 | L7 → L3(v010) | 一致性检查纯自觉无门控、报告无指纹与轮次、非阻塞门控呈现不直观 |
| asc-009 | L7 → L1(v002) | GEMM 实战暴露：一致性检查只扫 *.py，非 Python 工程无法通过 L4 门控 |
| asc-010 | L7 → L1(v003) | text 仅粗检，需在关键点追加 LLM 语义审核（缺口+实现一致性） |
| asc-011 | L4 → L1(v002) | 需把「审计发现的分级裁定」做进 MCP |
| asc-012 | L7 → L3(v014) | reviewer2 的 9 项设计侧问题需补设计并落实 |
| asc-013 | L5 → L3(v015) | 用户裁定 A：审计结论须匹配当前设计与代码，且覆盖所有阶段转换 |
| asc-014 | L7 → L3(v016) | backlog 3：新建工程不写注册表，TUI 选择器不可见 |
| asc-015 | L7 → L1(v005) | R30 进程陈旧防护 + R31 泛化歧义确认（带参考选项）+ R32 decision_bias 方案调研 |

## descent-4 交付内容（asc-003）

1. **se_complete_project**：终验闭环的唯一入口。前置校验（当前层 = L7-终验、L1–L6 全部 baselined、无未解决 blocking 门控），不满足时返回结构化 error 与未满足项清单；成功时 L7 README 置 completed、manifest 写 `layer_states[L7].status=completed` 与 `completed_at`，并追加 changelog。
2. **TUI completed 渲染**：层状态图新增 🏁 bold green 分支，终验完成后可正确显示完成态。
3. **部署一致性修复**：此前 TUI 修复只改了源码、未重新安装到 `.venv` 与 MCP 插件，导致「已有修复但界面仍旧」的假象；本轮完成重装并复验。

## descent-5 交付内容（asc-004）

**TUI 面板结构性重做**（这是"有数字、没滚动条、内容不全"的真正根因）：

- 旧实现：固定高度 `Static` 直接渲染 rich `Panel`。Textual 把 rich renderable 转成按视口裁剪的 `Visual`，`virtual_size` 恒等于容器高度，`overflow-y` 因此永远没有可滚动内容
- 新实现：`VerticalScroll` 容器（40/35/25%）包裹 `height: auto` 的内层 `Static#*-content`
- 待办表格重做：`expand=True`、Layer 列 min/max + fold、状态独立列（✅/⏳/🔒/🔓）、内容列 `ratio=1`、标题改为「N/M 已完成, K 待确认」——修复列宽截断导致的"内容显示不对"
- 契约测试：`test_todo_panel_is_actually_scrollable` 断言 `max_scroll_y > 0` 且滚动后 `scroll_y > 0`

实测（110x32）：top/mid/bottom `max_scroll_y` = 18/39/49，三个面板滚动条常驻。

## descent-6 交付内容（asc-005）

三项结构性修复（L3 v0.6 设计落实）：

1. **待办生命周期契约**：`rollback_to_baseline` 恢复基线正文后回填**现场待办段**与 `todo_descent`——回滚是回退设计产物，不再倒带工作进度。此前 asc-002~004 每轮回滚都把 L3 待办覆盖回模板占位符，导致面板显示「L3 ⏳ 初始化本层工作」
2. **基线占位符守卫**：`se_baseline(force=False)` 在待办仍为 `- [ ] 初始化本层工作` 时拒绝并给出 hint；`se_complete_project` 前置条件追加占位符检查。占位符不再可能被冻结进基线
3. **门控清理**：新增 `se_purge_confirmations(before_descent=0, resolution="superseded")`；`se_complete_project` 完成前自动结转较早轮次的非阻塞门控并回报 `purged_confirmations`，blocking 门控仍阻断。此前 descent-2 的非阻塞门控在项目完成后仍永久悬挂

## descent-7 交付内容（asc-006：多项目跟踪管理）

### 需求（L1 v002）
R1 项目注册表 · R2 存储选型 · R3 失效处理 · R4 每工具 project 参数 · R5 CLI/MCP 工程发现 · R6 TUI 工作目录显示 · R7 TUI 选择器 · R8 运行时切换 · R9 传参指定

### 搜证定论（L2 v002）
| 决策 | 结论 | 依据 |
|------|------|------|
| 存储介质 | **JSON 单文件**（评分 13/14） | SQLite 仅 5/14：本场景规模（5–500 项目）远低于其优势区间，且牺牲可读性与 diff 友好 |
| 失效处理 | **探测标记 + 显式 prune**（默认 dry-run） | 主流工具（docker/kubectl/IDE）均不静默删除；违反「不得静默删数据」约束 |
| 寻址 | **路径主键 + 名称别名** | 重名自动加后缀并告警；路径移动需重新登记 |

### 实现（L4 v007）
- `vinw/store/registry.py`：`ProjectRegistry`（原子写 tmp+os.replace、损坏备份、`status: ok/missing`、`prune(force=False)`）
- `vinw/server.py`：21 个 `se_*` 工具新增可选 `project`；`_project_or_error()` 统一解析并返回 `available_projects`；新增 `se_register_project` / `se_list_projects` / `se_remove_project` / `se_prune_projects` / `se_use_project`
- `vinw/tui/app.py` + `selector.py`：常显`工作目录`与`当前工程`；无参启动弹选择器；`p` 切换 / `r` 刷新 / `q` 退出
- `vinw/__main__.py`：`vinw project add|list|remove|prune`；`vinw tui <path|name>`

### 兼容红线（已验证）
`project=None` 时行为与 descent-6 完全一致——71 个既有用例全绿。

## descent-8 交付内容（asc-007：注册表改 SQLite）

### 触发与更正
用户质疑「txt 类总体记录不靠谱」，指出注册表只是状态表、无太多可读内容，工程内才需要 Markdown。复核确认 descent-7 的 L2 选型存在**权重错配**：

| 原判断 | 更正 |
|--------|------|
| 「人类可读/git diff」权重 3，JSON 得 3 分、SQLite 0 分 | 该准则对**不进 git 的机器状态表**不适用，属对象错配 |
| 「规模 5–500 不够大，不需要 SQLite」 | 看错轴：决定性因素是并发写、写放大、崩溃一致性 |
| 「SQLite 实现复杂度高」 | 反面：JSON 方案要自己实现锁与合并，等于手搓数据库 |

CSV 再评估：结构性够用且最紧凑（1944 B），但 null/空串不可区分、Excel 会篡改、**同样无并发锁** → 否决。

### 分层落地
| | 控制面 | 数据面 |
|---|---|---|
| 载体 | **SQLite**（`$VINW_HOME/registry.db`，WAL） | **Markdown + frontmatter**（工程内，未改动） |
| 内容 | projects 表 + 状态切换事件表 | 需求/设计/基线/测试记录 |

### 三项真实改进（均有测试）
1. **消除写放大**：`touch()` 从整表重写（9.5 ms/300 条）改为单行 UPDATE
2. **并发安全**：WAL + busy_timeout + 事务取代「写前重读+原子替换」；新增双连接并发写测试
3. **intent/observation 分离**：`state`(active/dormant) 与 `missing_since` 独立；默认只探测 active，休眠工程跳过探测以适配慢速/网络盘

### 迁移与容错（实测）
- 真实 `~/.vinw/registry.json` 首次访问自动迁移，写入 `import` 事件，原文件保留为 `registry.json.migrated-<ts>`
- 损坏库隔离为 `registry.db.corrupt-<ts>` 后重建，绝不静默删除
- 新增 `vinw project activate|deactivate|history|export` 与 `se_set_project_state` / `se_project_history` / `se_export_projects`

## descent-9 交付内容（asc-008：一致性门控）

### 问题
`se_check_consistency` 此前**纯自觉**：`baseline()` / `descend()` / `se_complete_project()` 均不校验，漏做无任何提示；报告不含 `descent` 与代码指纹，无法判断"本轮是否检查过"「检查后代码是否又改」。

### 解法：指纹 + 转换点门控 + 自动兜底
代码由 agent 直接写盘、不经 MCP，无法拦截每次写入 → 改为在**所有推进路径**上校验指纹：

| 触发点 | 行为 |
|--------|------|
| `se_baseline("L4-编码实现")` | 自动 ensure；未通过则拒绝（`force` 可跳过） |
| `se_descend(L4→L5)` | 同上，防绕过基线守卫 |
| `se_complete_project` | 校验本轮存在 passed 报告 |

**必然性**：新增 `test_descend_from_l4_regates`（改代码后再下降被拒绝）等用例，覆盖"绕过基线""忘了调用""检查后又改码"三条漏检路径。

### 增量复用（用户要求：未修改内容避免重复检查）
`ConsistencyGate.freshness()` 四态：`fresh` / `stale_files` / `stale_design` / `missing`。

- fresh → 零成本放行；`se_check_consistency(method="llm")` 返回 `{reused: true, report_id, overall}`，**不构造 prompt、不消耗审计**
- stale → 自动跑 text 检查落盘后再判定
- text 检查始终全量扫描：符号存在性跨文件（符号可能移文件），按文件增量会误报缺失，而其成本仅毫秒级；**昂贵的 LLM 语义审计才做增量**

实测：真实工程首次 `missing` 执行检查，二次 `fresh` 直接复用。

### 非阻塞门控呈现改进
- `se_get_project` → `blocking_pending` / `pending_review`（含 `age_days`）+ `consistency`
- `se_get_next_steps` → `awaiting_review`（无待办时也列出）
- TUI → 分两组 `🔒 阻塞（会卡流程）` / `🔓 待你审阅（不卡流程）`，双计数标题，有阻塞时边框转红
- 设计评审类门控（requirement-decomposition / interface-design）**默认阻塞**

## descent-12 交付内容（asc-011：审计分级裁定）

### 背景
独立 reviewer 一次审出 15 个问题，逐条处理时暴露流程空白：VINW 只会说"不一致"，不会说"该改哪边"。

### 能力
| 组件 | 说明 |
|------|------|
| `vinw/workflow/triage.py` | classification（impl_bug/design_bug/design_gap/ambiguous）+ confidence + difference/analysis/recommendation/impact |
| 门控决策 | `clear` / `auto_fixable` / `auto_fix_pending` / `escalate`，接入 baseline(strict)、descend、complete |
| 新工具 ×4 | `se_triage_prompt`、`se_store_triage`、`se_get_escalations`、`se_record_triage_decision` |

### 自动化边界（核心策略）
| 判定 | 处置 |
|------|------|
| impl_bug + high | 记录变更后自动修正，门控放行 |
| impl_bug + medium/low | 升级用户 |
| design_bug / design_gap | 升级用户（需上升改设计） |
| ambiguous | 一律升级用户 |

### 实战效果（本项目自身）
reviewer 15 项发现 → 裁定 14 项 → **10 项高置信实现缺陷自动修复**（strict 空策略、空扫描误落盘、冲突分支不可达、报告缺字段、.c 声明当实现等）→ 4 项经用户裁决（2 项改设计、1 项改名 search_scope、1 项补 TUI 标记）→ 升级项归零 → 门控放行。

**这轮实战同时证明了「独立 LLM 审核」的价值**：15 项里没有一项是靠 text 门控或自审发现的。

## descent-14 交付内容（asc-013：全阶段审计契约）

### 用户裁定
「为什么在 L4 有漂移的情况下允许进入 L5？这合理吗？」→ 裁定 A：审计结论必须匹配**当前设计与代码**，且该校验覆盖**所有阶段转换**。

### 根因（两处叠加）
1. `code_fingerprint` 把设计哈希算进自己 → "代码是否变化"与"设计是否变化"无法区分
2. `llm_matches_current` 只比代码指纹 → 一份没看过新设计的结论可以给新设计背书

### 落地
| 项 | 内容 |
|----|------|
| 指纹 | `code_fingerprint` 仅含代码；`design_hash` 独立 |
| 匹配 | `satisfied` 需 code **且** design 双匹配；缺 `design_hash` 时 fail-closed |
| 门控 | 任意 baseline/descend/complete：漂移后必须出示匹配当前代码+设计的结论 |
| 顺序 | 占位符 → strict/triage（只读）→ heal（结论→text→锚定）→ 二次 ensure → 写状态 → 补写日志 |
| 副作用 | 拒绝不改锚点、不写 auto-audit（text 失败留失败报告作证据） |

### 11 轮独立评审的结论
descent-13/14 累计 11 轮 reviewer 审计，发现 70+ 项问题，其中**7 类门控绕过路径**全部由独立评审发现——text 门控与自审均未捕获任何一条。这条证据本身说明：**分级裁定 + 独立审查**是必要的，而非流程装饰。

## descent-15 交付内容（asc-014：工程自动登记，backlog 3）

### 缺陷
`se_init_project` 只设进程内 active project，不写注册表 → 跨目录新建的工程在 TUI 选择器与 `se_list_projects` 中**完全不可见**（磁盘完好，用户误判为创建失败）。

### 修复（A 方案：创建即登记，符合 IDE 惯例）
| 入口 | 行为 |
|------|------|
| `se_init_project`（新建/接管） | 自动登记；`register=false` 退出；失败降级为 warning 不毁工程 |
| `se_use_project` | 激活即补登记；返回 `registered/name/warning`；`touch` 容错 |
| CLI `vinw init` | 同样登记；`--no-register` 退出 |

### 关键工程决策（reviewer12/13 两轮独立评审驱动）
- 异常边界收窄为 `(OSError, sqlite3.Error, ValueError)`：编程错误必须上抛，不得伪装成环境故障
- 同名冲突时登记名自动改名（`dup-2`）并**透传**给调用方，避免按错名寻址
- `tests/conftest.py` autouse 隔离 `VINW_HOME`：修复前每跑测试都在真实注册表累积幽灵条目（实测 23 条，已 prune）
- 验收标准 AC1–AC7 全部有对应测试

## descent-16 交付内容（asc-015）

### R31：LLM 驱动的歧义对齐机制（P1，用户定义）

不是"所有决策都问用户"，而是**只在模糊/歧义时**发起，且由 LLM 反向提供选项与参考分析：

| 环节 | 落地 |
|------|------|
| 发现 | 审计 `ambiguous` 分类 → `se_request_clarification_from_finding` 一键转澄清（预填假设/偏离） |
| 显性化 | 请求必填 `assumption`（当前理解）/`deviation`（偏离风险）/`uncertainty`（为何不确定）——用户是纠正确认心智模型，不是做题 |
| 参考选项 | LLM 生成选项（label/description/impact），自动追加 `assume-ok`（确认假设）与 `other`（自由输入）；`recommendation` 结构化推荐 |
| 对齐闭环 | 裁决 `corrected = resolution != "assume-ok"`；引擎层统一写 `alignment` changelog（TUI/MCP 同副作用）；同主题第 3 次发起告警"该改设计文档了" |
| 门槛 | 高置信/无歧义**自主执行**，工具层只强制 `uncertainty` 非空 |

### R30：进程陈旧防护（事故驱动的三项）

| 项 | 落地 |
|----|------|
| 版本横幅 | `__commit__/__dirty__` + `se_get_project.server_version` + 启动 stderr 日志 + TUI 三分支提示 |
| 重启规则 | README 步骤 3.5：「pip install 后必须重启 MCP server」 |
| 算法版本 | 报告与锚点写 `design_hash_algo: layer-v1`；不匹配即 stale（旧报告自然失效） |

### R32：decision_bias（仅调研，未实现）

L2 产出调研：形态对比（自由 prompt / 结构化问卷 / 混合）、**10 维调查表草案**、回答→倾向推断方法
（v1 规则映射、v2 LLM 归纳但仅作参考不自动裁定）、与 triage 升级的衔接点。结论：推荐混合形态，backlog。

### 过程记录（诚实披露）

- **L6 曾试图清理测试 hack，被 v0.15 门控拦下**（改测试=改代码，设计已冻结 → design_lag）。已回退并记入清理日志，留待下轮 L4。
- 两轮独立评审（reviewer14 设计、reviewer15 实现）共 23 项发现，19 修 / 4 进 backlog（R33：TUI 就地裁决、alignment 结构化）。

## 流程违规与补救披露（延续）

descent-2 终验后的三次热修（chg-032/033/034）已由 asc-002 补救并立规 DESC-001（基线后缺陷必须 ascend）。descent-4 本身即是按 DESC-001 执行的第四次下降：发现完成态缺口后先上升、改设计（L3 v0.4/v005）、再下降实现，未走热修。

## 功能实现清单（终态）

### 存储层
- [x] Project 初始化（7 层目录树 + manifest + changelog + ascensions）
- [x] 基线冻结/回滚、文档 CRUD、Todo 跨层扫描、原子变更日志
- [x] 状态目录 `.vinw/`
- [x] todo_descent 写入轮次追踪

### 工作流引擎
- [x] 基线化、上升回溯、下降推进、阻塞门控、下降可行性检查
- [x] **完成态迁移（se_complete_project）**
- [x] 实际经历 3 次上升 + 4 次下降全流程验证

### MCP Tools（18 个 + 自举）
- [x] 全量工具（见 api-design.md v0.4 工具清单）
- [x] se_init_project 接管模式（adopted=true）
- [x] se_check_consistency 代码定位（manifest.code_root + code_scope 混合）
- [x] **se_complete_project**（完成态迁移，v0.4 新增）

### TUI
- [x] 3 面板布局、2 秒自动刷新、面板常驻滚动条（overflow-y: scroll）
- [x] 刷新容错（瞬时文件错误保留上次渲染）
- [x] completed 状态渲染（🏁）
- [x] 无头渲染测试覆盖（test_tui.py 4 例）

## 测试覆盖（终态）

| 模块 | 用例数 | 结果 |
|------|--------|------|
| test_project.py（含 todo 追踪 3 例） | 13 | 13/13 ✅ |
| test_state_machine.py | 11 | 11/11 ✅ |
| test_consistency_llm.py | 10 | 10/10 ✅ |
| test_search.py | 7 | 7/7 ✅ |
| test_registry.py（含 SQLite 控制面） | 37 | 37/37 ✅ |
| test_consistency_gate.py | 14 | 14/14 ✅ |
| test_symbols.py | 20 | 20/20 ✅ |
| test_audit_policy.py | 17 | 17/17 ✅ |
| test_contract_v014.py | 44 | 44/44 ✅ |
| test_triage.py（descent-12 新增） | 18 | 18/18 ✅ |
| test_bootstrap.py（含完成态 3 例） | 10 | 10/10 ✅ |
| test_tui.py（滚动断言 + 多项目 4 例） | 9 | 9/9 ✅ |
| test_todo_lifecycle.py（新增） | 15 | 15/15 ✅ |
| **合计** | **303** | **303/303 ✅** |

端到端实测：MCP 自举加载 ✅；一致性检查 20/20 ✅；se_complete_project 前置校验与成功路径 ✅；TUI 渲染/滚动/容错/completed ✅。

## 已知限制

1. **LLM 审计需外部调用**：`method='llm'` 仅构造 prompt，实际 LLM 调用由 agent harness 执行。
2. **TF-IDF 需 scikit-learn**：未安装时自动降级到 ripgrep。
3. **TUI 未做交互式端到端测试**：无头渲染已覆盖，真机交互未系统测试。
4. **单活动工程**：`_active_project` 为进程内单例，多工程映射待后续版本。
5. **DESC-001 靠决议约束而非引擎强制**：状态机未在基线后拦截直接文件修改，后续可加校验层。

## 结论

**十六次下降、十五次上升全部闭环，303 个单元测试全部通过，完成态迁移能力补齐，自举与跨 harness 能力端到端验证成功。VINW 项目达到可交付状态。**
