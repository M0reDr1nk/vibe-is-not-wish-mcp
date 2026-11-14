---
created_at: '2026-11-13T10:02:20.514327'
layer: L1-需求拆解
se_version: '2.0'
updated_at: '2026-11-13T10:02:20.514327'
---

# 需求拆解

## 原始需求

构建一个跨 harness 可用的增强 agent 的软件工程过程控制引擎，核心功能：

1. 方案拆解
2. 近似现有方案搜集
3. 关键问题点列举分析 + 推荐选型供人工确认
4. 方案归档
5. 方案再细化
6. 接口设计
7. 启动编码及测试代码实现
8. 实现中对比设计文档进行一致性检查
9. 测试验证及 bugfix 及方案修正轮替迭代（含调试代码插入）
10. 最终检视清理及终验

贯穿要求：
- 严格文档代码一致性检查
- 变更点严格记录登记
- 与用户交互确认约定
- 过程信息严格归档

## 关键问题域

| 编号 | 问题域 | 说明 |
|------|--------|------|
| Q1 | 层级选择 | Skill vs MCP vs Agent 层级，如何跨 harness？ |
| Q2 | 状态机设计 | 线性推进 vs 螺旋上升-回溯-再下降？ |
| Q3 | 存储层 | 数据库存储 vs Markdown 分层组织？ |
| Q4 | 人类可读性 | 如何确保过程产物随时可被人工审阅？ |
| Q5 | 门控机制 | 如何强制人工确认，防止 agent 擅自推进？ |
| Q6 | 回滚机制 | 验证失败时如何显式回溯到上层基线？ |
| Q7 | 可视化 | 如何实时展示螺旋上升进度与 todo？ |

## 约束

- 必须跨 harness 可用（Kimi / Claude Desktop / Cursor / ...）
- 必须人类可读、git diff 友好
- 必须显式记录-回滚，非隐式覆盖
---

# descent-7 扩展需求：多项目跟踪管理（asc-006）

## 原始需求（用户原话要点）

> 需要支持对多个项目的跟踪管理，TUI 中显示工作目录以及传参指定或者在 TUI 里选择看哪个。应回到设计阶段，进行扩展分析然后再扩展实现。

确认的设计岔路（用户裁决）：
- MCP 侧：**每个工具增加可选 `project` 参数**（而非全局单活动 + 切换）
- TUI 侧：**无参启动弹选择器 + 快捷键切换**
- 注册表：待分析——「是否需要在合适目录用简单的 db 保存」「失效工程是否需要自动清理」

## 需求拆解

| 编号 | 子需求 | 优先级 | 约束/验收 |
|------|--------|--------|-----------|
| R1 | 项目注册表：登记多个 VINW 工程（名称、路径、创建/最近访问时间、状态） | P0 | 跨仓跨目录可用；可人工检视 |
| R2 | 注册表存储选型：JSON 文件 vs SQLite（"简单的 db"） | P0 | 需给出权衡分析并定论 |
| R3 | 失效工程处理：路径被删/不再是 VINW 工程时如何表现，是否自动清理 | P0 | 不得静默丢数据；用户可预期 |
| R4 | MCP 多项目寻址：所有 `se_*` 工具支持可选 `project` 参数 | P0 | 向后兼容（省略参数时行为不变）；非法 project 返回结构化错误 |
| R5 | 工程发现：`vinw project add/remove/list` CLI + MCP `se_register_project` / `se_list_projects` | P1 | 支持路径自动探测 `.vinw/manifest.md` |
| R6 | TUI 显示工作目录：常显当前查看的工程路径与名称 | P0 | 与 manifest.name 一致 |
| R7 | TUI 选择器：无参启动列出已注册工程 + 当前目录工程，键盘选择 | P0 | 空注册表时给出引导而非崩溃 |
| R8 | TUI 运行时切换：快捷键在已注册工程间切换，无需重启 | P1 | 切换后所有面板立即刷新 |
| R9 | TUI 传参指定：`vinw tui <path|name>` 直接进入指定工程 | P0 | 兼容现有 `vinw tui vinw-design` 用法 |

## 关键问题域（新增）

| 编号 | 问题域 | 说明 |
|------|--------|------|
| Q8 | 注册表存储介质 | JSON 文件（可 diff、无依赖）vs SQLite（事务、并发、海量）——需按实际规模定论 |
| Q9 | 失效工程策略 | 自动删除（危险）vs 标记 stale 并可手动 prune vs 每次访问探测 |
| Q10 | 并发写入 | 多个 harness / TUI 同时写注册表时的原子性 |
| Q11 | 向后兼容 | 现有单工程调用（无 project 参数、cwd 自举）必须不破坏 |
| Q12 | 身份标识 | 用路径、名称还是稳定 id 寻址工程；重名与移动路径如何应对 |

## 约束（继承 + 新增）

- 继承：跨 harness、人类可读、git diff 友好、显式记录
- 新增：**不得静默删除用户数据**（失效工程只能标记或经显式 prune）
- 新增：**未传 project 参数时行为与现在完全一致**（自举 + 单例）

---

# descent-10 候选需求：模糊需求的反向提问（backlog，2026-11-14）

## 触发

在用 GEMM 工程实战验证 VINW 时发现：L1 只有"agent 自行拆解 + 人工批准"的环节，缺少**主动追问澄清**的机制。当原始需求含糊（如"做一个加速实现"未界定数据类型、是否允许调用系统 BLAS、目标矩阵规模），agent 倾向于自行假设后一路往下走，错误要到 L4/L5 才暴露，代价高。

## 需求草案

| 编号 | 子需求 | 优先级 |
|------|--------|--------|
| C1 | L1 增加 `requires_clarification` 判定：拆解时识别"关键歧义点"（影响架构/接口/验收的） | P0 |
| C2 | 结构化追问：以列表形式提出具体问题并给出推荐默认值，而非开放式提问 | P0 |
| C3 | 未澄清则拦截：存在未回答的关键歧义时，拒绝 L1 基线或禁止降入 L3 | P0 |
| C4 | 歧义留痕：把"问了什么、答了什么、因此改了什么"写入 L1 proposals.md 与 changelog | P1 |
| C5 | 与既有门控整合：复用 `se_require_confirmation`（item_type = ambiguity-clarification） | P0 |

## 状态

Backlog — 待下一轮上升（asc）时纳入正式 L1 拆解与 L3 设计。

---

# descent-10 候选需求：新建工程后 TUI 选择器看不到（backlog，2026-11-14）

## 现象

在 `example/gemm` 用 `se_init_project` 新建工程后，TUI 工程选择器（`p` 键）里**看不到 gemm**，只有已注册的 `vinw-self-design`。

## 复现

1. `se_init_project(name="gemm", path=".../example")` → 工程创建成功
2. `vinw tui`（cwd = vinw 代码仓）→ 按 `p`
3. 列表只有 `vinw-self-design` 与「当前工作目录工程 vinw-self-design」，无 gemm

## 根因（已核对代码）

| 事实 | 位置 |
|------|------|
| `se_init_project` 创建工程后**只设置 `_active_project`，不写注册表** | `vinw/server.py::se_init_project` |
| TUI 选择器数据 = `registry.list()` + `_cwd_project()` | `vinw/tui/app.py::action_select_project` |
| `_cwd_project()` 只探测 `cwd/vinw-design` 与 `cwd` 本身 | `vinw/tui/app.py::_cwd_project` |

→ gemm 既不在注册表里，也不在 cwd 下（cwd 是代码仓，其内只有 `vinw-design`），故不显示。

实测注册表内容：仅 `vinw-self-design` 1 条。

## 影响

- 用户按文档流程"新建工程 → 打开 TUI"，会以为工程丢了
- `se_use_project` 同样不登记，靠名称寻址时后续调用会失败
- 属**可用性缺陷**，非数据丢失（`se_list_projects` 也看不到，但磁盘文件完好）

## 修复建议（待设计）

| 方案 | 说明 | 倾向 |
|------|------|------|
| A. `se_init_project` 成功后自动 `registry.add()` | 一行改动，符合"创建即登记"直觉；需考虑用户是否想登记临时工程 | **推荐（默认开启，可用 `register=false` 关闭）** |
| B. `se_use_project` 时自动补登记 | 兜底，防止漏登记 | 推荐（一并做） |
| C. TUI 增加「扫描发现未登记工程」分区 | 信息更全，但需要扫描目录，慢盘上有成本 | 可选 |
| D. `se_list_projects` 增加 `discovered` 分区（未登记但存在） | 折中，读注册表后扫一层 | 可选 |

## 状态

Backlog — 与「模糊需求反向提问」一并纳入下一轮上升（asc）的 L1 拆解。

---

# descent-10 缺陷记录：一致性检查器不支持非 Python 工程（backlog，2026-11-14）

## 现象（GEMM 工程实测，descent-2）

`se_baseline("L4-编码实现")` 被一致性门控拒绝：

```
L4 一致性校验未通过（overall=warning，2 项不一致）
```

报告 `report-7366f67f.md` 内容：

| ID | 描述 |
|----|------|
| INC-001 | Design symbol `GEMM_H` not found in code |
| INC-002 | Design symbol `enum` not found in code |

匹配项 **0**。而实际 C 实现里 `gemm_f32`、`gemm_mr`、`pack_a`、`macro_kernel` 等 17 个接口全部存在且测试通过。

## 根因（代码定位）

| 位置 | 问题 |
|------|------|
| `consistency_llm.py::_collect_code_files` | `rglob("*.py")` 写死 → C/C++/Rust/Go 工程扫不到任何代码文件 |
| `consistency_llm.py::_extract_symbols` | 仅识别 `def`/`class`、表格内 `foo(`、反引号 `se_*`；不认 C 的 `gemm_f32(` 声明、`#define`、`enum` |
| 结论 | 扫不到代码 → 全部设计符号"缺失"；且把头文件宏 `GEMM_H`、C 关键字 `enum` 误当符号 → **既漏检又误报** |

## 影响

- **非 Python 工程无法通过 L4 基线门控**，只能 `force=true` 绕过（等于门控失效）
- 门控在 Python 工程上可用（自举工程已验证），但覆盖面被锁死在单一语言
- 严重性：高（VINW 定位为跨语言通用过程控制）

## 修复建议

| 编号 | 措施 |
|------|------|
| F1 | manifest 增加 `code_extensions: [".py", ".c", ".h", ".cpp", ".rs", ".go"]`，默认含常见语言 |
| F2 | 符号提取改为**代码文件内反查**：把设计文档里出现的标识符（`[A-Za-z_]\w*`）与代码中的函数/宏/类定义比对，而非只靠设计侧正则 |
| F3 | 过滤语言关键字与文件保护宏（`enum`、`GEMM_H` 这类） |
| F4 | 报告里列出"扫描到的文件数"，为 0 时明确报错而非静默产出假 warning |

---

# descent-10 缺陷记录：门控错误提示错位（backlog，2026-11-14）

## 现象

GEMM 工程 L4 基线因**一致性校验失败**被拒，但返回的 `hint` 是：

```
"hint": "调用 se_update_todo 填写真实待办，或传 force=true"
```

—— 这是**待办占位符守卫**的提示文案，与真实失败原因（一致性）无关。

## 根因

`vinw/server.py::se_baseline` 的 `except ValueError` 分支里 hint 是写死的字符串，而该处会捕获**两种** ValueError：占位符守卫、一致性门控。

## 影响

误导用户去改 todo（无效操作），掩盖真实原因。严重性：中（可用性）。

## 修复建议

根据异常类型区分 hint（自定义异常类 `PlaceholderTodoError` / `ConsistencyGateError`），或直接把 `str(e)` 作为主提示、hint 只给通用的 `force=true` 说明。

---

# descent-10 正式需求：跨语言一致性检查 + 门控提示准确（2026-11-14）

## 背景

GEMM 实战（C 工程）暴露：一致性检查器只扫 `*.py`、只认 Python 符号 → 非 Python 工程 L4 门控必然失败，只能 force 绕过。

## 需求拆解

| 编号 | 子需求 | 优先级 | 验收 |
|------|--------|--------|------|
| R10 | 一致性检查支持多语言：`code_extensions` 可配置（默认含 py/c/h/cpp/cc/hpp/rs/go/java/ts），按扩展名收集代码文件 | P0 | C 工程能扫到 `.c/.h` 并提取函数符号 |
| R11 | 符号提取改为**双语对照**：代码侧按语言正则提取定义（函数/宏/类/结构体），设计侧提取标识符，取交集判定存在性 | P0 | `gemm_f32`、`macro_kernel` 等被识别；不再靠 `def/class` |
| R12 | 关键字与保护宏过滤：`enum/struct/int/void` 等语言关键字、`FOO_H` 头文件保护宏不计入符号 | P0 | GEMM 报告中不再出现 `GEMM_H`、`enum` |
| R13 | 扫描为空要显式报错：`files_scanned == 0` 时返回明确错误（含已配置扩展名），不得产出"全缺失"的假报告 | P0 | 错误信息可直接定位配置问题 |
| R14 | 门控错误提示准确：自定义异常类型区分"占位符守卫"与"一致性门控"，hint 与真实原因一致 | P1 | 一致性失败时不再提示去改 todo |
| R15 | 报告可观测字段：`files_scanned`、`extensions`、`code_symbols_count` 写入报告 frontmatter | P1 | 报告自解释 |

## 非目标

- 不做 AST 级解析（保持正则 + 语言规则表，够用且无依赖）
- 不做跨语言语义理解（那是 `method="llm"` 的职责）

---

# descent-11 正式需求：分层审计契约（2026-11-14）

## 分析结论（本次讨论核心）

| 检查 | 逻辑性质 | 能保证 | 不能保证 |
|------|---------|--------|---------|
| text 符号检查 | 必要条件（单向） | 设计提到的接口在代码中就位（防漂移） | 语义/逻辑/数据结构是否正确 |
| LLM 语义审核 | 启发式 | 发现"设计要求了但缺代码/缺测试"的盲区 | 数学正确性（需测试） |
| L5 测试 | 可执行验证 | 测试覆盖范围内的行为正确 | 未覆盖的设计条款 |

→ text 通过**不等于**一致；text 失败**也不一定**是代码问题（可能是提取器缺陷，GEMM 已实测）。
→ 语义保障的真正主体是**测试**；LLM 的不可替代价值是**覆盖率视角的缺口发现**。

## 需求

| 编号 | 子需求 | 优先级 |
|------|--------|--------|
| R16 | 审计策略可配置：`consistency_policy` = `text` / `text+llm`（默认）/ `strict` | P0 |
| R17 | 关键点强制 LLM：`text+llm` 下，L4→L5 下降与项目完成前必须出示本轮 LLM 审核结论 | P0 |
| R18 | LLM 审核目标升级：**A 缺口清单**（设计要求但缺代码/缺测试）+ **B 实现一致性**（逻辑/数据结构/约束/接口，带 design↔code 证据） | P0 |
| R19 | 报告记录审查者：`auditor`(self/reviewer)、`auditor_model`、`kind`(text/llm)、`policy` | P0 |
| R20 | `tooling_discrepancy`：text=warning 而 LLM=passed 时标记冲突并拒绝自动放行 | P0 |
| R21 | 报告区分 text/llm；门控按 kind 取最近通过报告 | P0 |

## 非目标

- 不做自动修复；MCP server 仍不自己调模型（"出题+答题"两步）

---

# descent-12 正式需求：审计发现的 LLM 分级裁定（2026-11-14）

## 背景

独立 reviewer 一次审出 15 个问题（6 缺口 + 9 不一致）。逐条处理时暴露流程空白：**VINW 只会说"不一致"，不会说"该改哪边"**。人工判断成本高、易漏，且"实现错了"与"方案错了"的处置路径完全不同（前者改代码，后者改设计并可能推翻已批准契约）。

## 需求

| 编号 | 子需求 | 优先级 |
|------|--------|--------|
| R22 | LLM 审核输出增加**分级裁定**字段：`classification` ∈ `impl_bug` / `design_bug` / `design_gap` / `ambiguous`；`confidence` ∈ `high` / `medium` / `low`；`recommendation` 文本 | P0 |
| R23 | 裁定规则写入提示词：先判断"设计本身是否合理"，再判断"实现是否偏离设计"；不得默认"实现错" | P0 |
| R24 | **高置信实现错（impl_bug + high）可自动修正**：允许在记录 `se_log_change` 后直接改实现并标记 `fixed`；门控对这类不再阻断 | P0 |
| R25 | **其余情况必须升级用户**：生成结构化待决项（finding_id、差异点、分析、推荐、影响面），通过门控拦截，并在 `se_get_project` / `se_get_next_steps` / TUI 中可见 | P0 |
| R26 | 用户裁定留痕：`se_record_triage_decision(finding_id, decision, note)`，decision ∈ `fix_impl` / `fix_design` / `accept_as_is` / `defer` | P0 |
| R27 | 新工具 `se_get_escalations`：列出所有待用户裁决项（含差异点/分析/推荐），支持按轮次过滤 | P0 |
| R28 | 门控语义：LLM 报告存在 `ambiguous` 或 `design_*` 且未裁决时 → 阻断下降与完成；全部为 `impl_bug/high` 且已 `fixed` → 放行 | P0 |

## 非目标

- 不自动改设计（改设计必须走上升 + 人工批准）
- 不自动判断"设计对错"的最终权威——LLM 裁定只是初判，`ambiguous` 一律交人

---

# descent-12 遗留特性：决策倾向性配置（backlog，2026-11-14）

## 需求（用户提出）

增加"决策倾向性"配置输入，作为 LLM 裁定的**推荐依据**，并在**高置信场景**下作为自动决策的依据。

## 需求草案

| 编号 | 子需求 | 优先级 |
|------|--------|--------|
| B1 | manifest 增加 `decision_bias` 配置：`prefer` ∈ `fix_impl` / `fix_design` / `ask`；`auto_fix_max_risk` ∈ `low` / `medium`；`allow_auto_design_change` bool（默认 false） | P1 |
| B2 | `se_triage_prompt` 把 `decision_bias` 注入提示词：LLM 的 `recommendation` 必须与倾向一致或明确说明为何偏离 | P1 |
| B3 | 自动决策上限：`prefer=fix_impl` 时高置信 impl_bug 直接允许自动修正；`prefer=ask` 时**任何**发现都升级人工（含 impl_bug/high） | P1 |
| B4 | 设计类问题永不由 bias 自动放开：`design_bug`/`design_gap` 始终需要人工批准（`allow_auto_design_change` 仅生成"待批方案"而非直接改） | P0 |
| B5 | bias 变更留痕：写入 changelog，报告中记录当次生效的 bias，便于事后解释"为什么当时自动修了" | P1 |
| B6 | 与强制门控的关系：bias 只能**收紧或放宽自动修正范围**，不得绕过 LLM 审核本身 | P0 |

## 设计要点（待 L3 细化）

- bias 属于"策略而非数据"，应可被项目级 manifest 覆盖，也可被调用方在单次调用中显式覆盖（后者需记录在报告中）
- 风险等级来源于 finding 的 `severity` + 影响面（是否触达已批准基线/公开契约）
- 与既有 `consistency_policy`（决定要不要审核）正交：本项决定"发现问题后怎么处置"

## 状态

Backlog — 待下一轮上升（asc）时纳入 L1 正式需求与 L3 设计。与「模糊需求反向提问」「新建工程 TUI 不可见」并列。
