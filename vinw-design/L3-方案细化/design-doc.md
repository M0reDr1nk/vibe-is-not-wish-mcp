---
created_at: '2026-11-13T10:02:22.471783'
layer: L3-方案细化
se_version: '2.0'
updated_at: '2026-11-13T10:02:22.471783'
---

# SE-MCP v2 设计方案

## 架构决策

### 决策 1: MCP + Skill 双层架构

- 备选方案: 纯 Skill / 纯 MCP / 纯 Agent
- 选择理由: MCP 跨 harness + Skill 工作流指导，互补
- 拒绝理由:
  - 纯 Skill 不可跨 harness
  - 纯 MCP 无工作流编排，agent 不知道何时调用什么
  - 纯 Agent 无通用框架

### 决策 2: Markdown 分层存储

- 备选方案: SQLite / 混合
- 选择理由: 人类可读、git diff 友好、任何文本工具可打开
- 拒绝理由:
  - SQLite 不可读，需要导出工具
  - 混合复杂度翻倍，同步风险

### 决策 3: 螺旋上升状态机（替代线性推进）

- 备选方案: 线性 7 phase
- 选择理由:
  - 软件工程天然需要回溯（需求理解偏差、设计缺陷、测试失败根因）
  - 显式基线 + 上升记录 = 完整审计链
  - 线性推进无法处理"验证失败回设计再分析"的场景
- 拒绝理由: 线性状态机无法表达上升-再下降的轮替循环

## 数据模型

### 项目目录树

```
my-project/
├── .vinw/
│   ├── manifest.md          # 全局状态机
│   ├── changelog.md         # 追加式变更日志
│   ├── ascensions.md        # 上升回溯记录
│   └── decisions.md         # 跨层决策
├── L1-需求拆解/
│   ├── README.md
│   └── proposals.md
├── L2-参考文献与方案搜证汇总/
│   ├── README.md
│   ├── references.md
│   ├── evidence-matrix.md
│   └── synthesis.md
├── L3-方案细化/
│   ├── README.md
│   ├── design-doc.md
│   └── api-design.md
├── L4-编码实现/
│   ├── README.md
│   ├── implementation.md
│   └── .baseline/
│       └── v001.md
├── L5-测试验证/
│   ├── README.md
│   ├── test-plan.md
│   └── debug-sessions/
├── L6-检视清理/
└── L7-终验/
```

### Manifest 状态机 (YAML Frontmatter)

```yaml
current_layer: "L3-方案细化"
current_descent: 3
layer_states:
  L1-需求拆解:
    status: "baselined"
    latest_baseline: "v001"
    descent_count: 1
  L2-参考文献与方案搜证汇总:
    status: "baselined"
    latest_baseline: "v002"
    descent_count: 2
    active_ascent: "asc-002"
  L3-方案细化:
    status: "in_progress"
    latest_baseline: null
    descent_count: 2
ascent_history:
  - id: "asc-002"
    descent_before: 2
    from_layer: "L5-测试验证"
    to_layer: "L2-参考文献与方案搜证汇总"
    to_baseline: "v002"
    reason: "..."
    descent_after: 3
pending_confirmations: []
```

## 核心流程

### 状态机操作

1. **baseline(layer, reason)**:
   - 将当前层 README.md 复制到 `.baseline/vXXX.md`
   - 更新 manifest: status → baselined, latest_baseline → vXXX
   - 追加 changelog

2. **ascend(from_layer, to_layer, to_baseline, reason)**:
   - 校验: to_layer 必须在 from_layer 之上
   - 校验: to_baseline 必须存在
   - 生成 ascent_id, descent_count + 1
   - 回滚目标层到基线（基线→工作区）
   - from_layer 至 L7 标记 superseded
   - 更新 manifest: current_layer, current_descent
   - 追加 ascensions.md + changelog.md

3. **descend(to_layer, reason)**:
   - 校验: to_layer 必须在当前层之下
   - 校验: 中间层必须已 baselined
   - 目标层标记 in_progress（清除 superseded）
   - 更新 manifest: current_layer
   - 追加 changelog

4. **require_confirmation / resolve_confirmation**:
   - 创建/解决阻塞性门控项
   - 存储于 manifest.pending_confirmations
   - se_can_descend 检查未解决阻塞项

### 决策 4: 一致性检查 — LLM 文本审计 + tree-sitter 预留

- 当前方案: **LLM 文本审计**
  - 将 design-doc/api-design 全文 + 代码全文传给 LLM，要求其比对并报告不一致
  - 结果写入 `consistency-reports/report-XXX.md`（含 before/after、严重程度、建议）
  - 优势: 无需额外依赖，对任何语言有效，能捕捉语义级不一致（如"设计说缓存 5min 代码写 10min"）
  - 局限: 结果质量依赖 LLM，需要结构化 prompt 约束输出格式
- tree-sitter 强校验:
  - 保留为**扩展能力**，pyproject.toml 已列入依赖
  - 当接口签名漂移成为上升回溯主因时，可启用 AST 级字段比对
  - 启用条件: 连续 2 次以上因接口签名不一致触发 ascend，或用户显式要求

### 决策 5: 向量检索 — TF-IDF + ripgrep

- 当前方案: **ripgrep 文本搜索为主**
  - 在 L2 阶段，agent 通过关键词搜索 references.md、历史项目目录
  - 零依赖、毫秒级、完全离线
- TF-IDF 增强:
  - 当历史项目 > 50 个或文本搜索质量不足时启用
  - 对已有方案文档做 TF-IDF 矩阵，query 做余弦相似度排序
  - sklearn 通常已装，代码 < 50 行，无缝升级
- faiss 降级为**远期备选**:
  - 仅当历史项目 > 500 个且 TF-IDF 明显不足时考虑
  - 当前是过度设计，不预支未发生的复杂度

## 技术栈

| 层 | 库/工具 | 说明 |
|----|---------|------|
| MCP Server | `mcp` (Python SDK v2.x, MCPServer) | 跨 harness |
| 文件存储 | `pathlib` + `python-frontmatter` | Markdown + YAML frontmatter |
| TUI 渲染 | `textual` + `rich` | 3 面板实时刷新 |
| 语法解析 | `tree-sitter` | **预留扩展**，接口已留好 |
| 向量检索 | `sklearn` (TF-IDF) + `ripgrep` | TF-IDF 按需启用，ripgrep 默认 |

## 变更记录

| 变更ID | 时间 | 内容 | 原因 |
|--------|------|------|------|
| chg-001 | 2026-11-13 | 增加 L2 证据层 | 需求：显式参考文献搜证阶段 |
| chg-002 | 2026-11-13 | 线性状态机 → 螺旋上升 | 需求：显式回溯-再下降循环 |
| chg-003 | 2026-11-13 | 一致性检查：LLM 文本审计 + tree-sitter 预留 | 用户决策 |
| chg-004 | 2026-11-13 | 向量检索：TF-IDF + ripgrep，faiss 降级为远期备选 | 用户决策 |
---

# descent-13 状态机合理性审查与状态同步契约

## 审查结论：状态机设计总体成立，但缺"状态归属"契约

### 状态词汇与转移（审查后的完整定义）

| 状态 | 含义 | 可进入来源 | 可离开去向 |
|------|------|-----------|-----------|
| `pending` | 从未开工 / 被放弃 | 初始化；**descend 放弃未基线层**（记 `abandoned_at`） | `in_progress`（descend/ascend 进入） |
| `in_progress` | 当前正在做 | descend / ascend 进入；baseline 后重入 | `baselined`（冻结）、`superseded`（上升） |
| `baselined` | 已冻结可回溯 | baseline | `in_progress`（重做）、`superseded`（上升） |
| `superseded` | 本轮作废、需重做 | ascend 使然；**或下层重新基线使上层依据失效（v0.19）** | `in_progress`（descend 重入）、`baselined`（重做后冻结） |
| `completed` | 项目终验完成（仅 L7） | complete_project | `in_progress`（ascend 回到 L7？实际 L7 被 superseded） |

不变量（修正后表述，均已在测试中断言）：
1. **至多一层**为 `in_progress`；当 `current_layer` 尚未冻结且项目未完成时，恰为该层。
   （冻结当前层后、以及项目完成后，`in_progress` 层数为 0 —— 原"恰好一层"表述为恒假命题）
2. `completed` 只允许出现在 L7
3. 由 `ascend` / `_invalidate_below` / **`_invalidate_above`（下层重新基线）** 产生的
   `superseded` 必带 `superseded_by`；若失效的层正是 `current_layer`，该层保持 `in_progress`
   并置 `needs_redo=true`（不能出现"当前层已作废且无工作层"的状态）
4. 进入/重做某层时，`needs_redo` / `superseded_by` / `superseded_at` 必须清除

### 发现的缺陷（本轮已修）

| 缺陷 | 影响 | 修复 |
|------|------|------|
| **状态双写不同步**：manifest 与各层 README frontmatter 各自维护 status，实测 7 层里 6 层不一致 | 人读 README 得到过期状态；`get_todos` 用 README 状态过滤 superseded，导致该过滤是死代码 | 明确 **manifest 为唯一状态机**，README 为镜像；新增 `_sync_layer_status()` 在所有转移处同步，`sync_all_layer_readmes()` 修历史分歧 |
| `descend` 未清除 `needs_redo`/`superseded_by` | 重做后仍显示"设计滞后/待重做" | 进入层时清除三个残留键 |
| `baseline` 未清除 supersede 标记 | 重新冻结的层仍留着旧的 superseded 痕迹 | baseline 时清除 |
| `layer_design_hash` 把 L3/README.md 算入设计哈希 | 同步状态 = "设计变了"，制造假漂移 | 设计哈希排除 README.md（状态载体，非设计文档） |
| `repair_ascend_state` 首版把当前层也标记为 superseded | 当前层消失，流程无法继续 | 修复后保留 current 层为 in_progress |
| `get_todos` 过滤依据错误 | 已作废层的待办仍出现在列表 | 改按 manifest 的 status 过滤 |

### 设计层面的结论

- 状态机**语义**合理（螺旋上升需要 superseded/needs_redo 承载"作废待重做"）
- 缺失的是**状态归属契约**：谁写、写几处、如何镜像。本版补齐为"manifest 唯一 + README 镜像 + 转移处强制同步"
- `repair_ascend_state()` 作为**状态修复能力**保留：历史上已产生过错误状态（旧版本 ascend 范围不全），需要可重复修复而非一次性脚本

---

# descent-21 补欠账：开发工具脚本（scripts/）的设计覆盖（严格路径正规化）

## 背景

`scripts/` 下有一批开发侧 helper 脚本（populate/finalize/l*-finalize/run_consistency_check/gen_tool_catalog 等），
descent-20 新增 `scripts/readme_stats.py`（README 统计的可复现脚本）时未同步设计 → design_lag 漂移。
按用户裁决走**严格路径**（零特例）：在 L1 阶段先最小补设计覆盖，heal 重锚后漂移消除。

## 契约（新增）

| 项 | 内容 |
|----|------|
| 定位 | `scripts/` 为**开发侧工具**，不属于 MCP 运行时（`vinw/`），不进工具清单，不改运行时行为 |
| 分类 | 一次性流程脚本（populate/finalize/l*-finalize）；可复现统计脚本（`readme_stats.py`）；目录生成（`gen_tool_catalog.py`，产物已入 api-design 工具清单） |
| `readme_stats.py` | 只读统计：从 `L4-编码实现/consistency-reports/` 按内容哈希去重计数 LLM 审计发现，口径写在其 docstring；README「Self-hosting Record」数字**以该脚本输出为准** |
| 变更纪律 | 脚本变更与 `vinw/` 代码同等对待：走螺旋流程（本条款即 descent-21 对其的正规化）；脚本的代码指纹计入一致性扫描（默认扩展名 `.py`） |
| 新增脚本 | 新增长驻/可复用脚本（如 readme_stats.py 这类）必须在设计文档登记一句定位，防止再次出现"代码先行、设计滞后" |

## 影响

- 设计哈希变化（本条款入 design-doc.md）→ 与代码侧新增的 readme_stats.py 同步 → design_synced →
  转换点 heal 自动重跑 text 检查并重锚，漂移消除
- 本条款同时是 R39（文档）的实现依据之一

---

# v0.23 接管现有代码仓（descent-21 / asc-020，R36-R40）

## 设计决策

| 决策 | 结论 | 理由 |
|------|------|------|
| D1 | adopt 是 `se_init_project` 的**参数**（`adopt_existing: bool = False`），不新增工具 | 接管语义已在该工具（adopted=true）；工具数稳定（40 不变），目录生成与契约测试零改动 |
| D2 | 布局默认**仓库根就地**；子目录布局保留为绕行 | 用户诉求是"在现有仓初始化"；就地布局让 `vinw tui <repo>`/`vinw status <repo>` 直接可用 |
| D3 | `work_mode` 为**纯元数据**，不加状态机 | 仅 next_steps 换提示文案；零门控语义变化（L2 结论 3） |
| D4 | 零新检查系统：摸底修正循环复用 `TextConsistencyChecker`，锚定复用 `ensure()`，存量处置复用 triage `accept_as_is`/`defer` | R40 机制边界约束 |
| D5 | 脚手架提取共享 helper（`init` 与 `adopt` 共用层目录/模板/manifest 生成） | 防两岔漂移；init 的空目录守卫与 adopt 的冲突守卫各自独立 |

## R36：`Project.adopt()` 与入口契约

### 守卫（拒绝 = 结构化 error，不抛裸异常）

| 守卫 | 行为 |
|------|------|
| root 不存在 | error：`目录不存在` |
| root 不是目录 | error |
| `.vinw/manifest.md` 已存在 | 不走 adopt（调用方返回幂等 adopted，现有行为） |
| `.vinw/` 存在但 manifest 缺失 | error：`检测到半初始化状态 <绝对路径>/.vinw（manifest 缺失），请清理后重试` |
| 任一**层目录名**已存在且非空 | error + `conflicts: [...]` + hint：改用子目录布局（`se_init_project(name="vinw-design", path=...)`） |
| 层目录存在但为空 | 允许（复用该目录，mkdir exist_ok 语义） |

### manifest 附加字段（仅 adopt 写入）

```yaml
work_mode: "existing-codebase"
code_root: "."
adopted_at: "<ISO8601>"
```

绿地工程不写 `work_mode`（缺省即绿地）；`next_steps` 判定 `manifest.get("work_mode") == "existing-codebase"`。

### changelog

adopt 成功追加 `change_type: "adopt"` 条目（scope=工程根，reason 含触发场景描述）。

### `se_init_project` 变更

- 新参数 `adopt_existing: bool = False`
- `adopt_existing=false`（默认）：**行为逐字节不变**（兼容红线，既有用例全绿）
- `adopt_existing=true`：`root = Path(path).expanduser().resolve()`（**不再拼 name**；name 仅作 manifest/注册名）
- 成功响应增加 `adopted_existing: true, work_mode, code_root`
- 守卫拒绝 → `{"error": ..., "conflicts": [...]?, "hint": ...}`（不创建任何文件）

### CLI

`vinw init <path> --name <name> [--adopt-existing] [--no-register]`：adopt 成功打印 `Adopted existing repo: <root>` + `work_mode: existing-codebase` + 提示 `vinw tui <name>`。

## R37/R38：`se_get_next_steps` 引导 + L1 待办种子

### work_mode == "existing-codebase" 时

- L1 `work` 替换为摸底清单（见 R38）；`gate` 文案加"（含现状摸底确认）"
- L4 `work` **整体替换**为就地修改清单（含 "Modify existing code in place"）；`special_instruction` = 摸底→检查→修正→锚定四步 + 首次 LLM 审计预期
- `special_instruction` 在 existing-codebase 模式下对**所有层**生效（asc-021 修订：INC-002 裁定，替换语义 + 全层提示为设计本意）

### L1 待办种子（R38，adopt 时写入，替换模板占位符）

```markdown
## 当前待办

- [ ] 现状摸底：通读现有代码与文档，产出《现状摸底》（结构见 R40）写入 L1 proposals「现状」节
- [ ] 明确本次变更范围（feature / extension / bugfix）与验收标准，写入 proposals
- [ ] 标注关键歧义点（必要时 se_request_clarification）
- [ ] 初始一致性检查：text 检查《现状摸底》↔ 代码，修正循环至 passed（首次锚定变更前指纹）
- [ ] 初始 LLM 审计：存量发现逐条裁决 accept_as_is / defer，债务清单入 proposals「legacy-debt」节
```

（占位符守卫天然通过：待办已不是模板行；但仍须逐条勾选后才允许 L1 基线。）

## R40：现状摸底与初始锚定契约

### 《现状摸底》结构（L1 proposals「现状」节，必填）

| 小节 | 内容 |
|------|------|
| 概述 | 一句话：这是什么系统、做什么 |
| 模块与入口 | 目录/模块划分、公开入口（API/CLI/主流程） |
| 公开契约 | 对外接口签名/协议/配置键（现状，非目标态） |
| 关键数据结构 | 核心模型/表/消息格式 |
| 构建与测试 | 如何构建、跑测试、现状测试覆盖概况 |
| 已知债务 | 代码中可见的不良结构/TODO/文档缺口（摸底时观察到什么写什么） |

### 修正循环（复用机制，无新工具）

1. `se_store_document` 写入摸底节
2. `se_check_consistency(method="text")` → 不一致 = 摸底文档写错（或真债务）→ 修文档/记债务 → 重跑
3. 终止条件：`overall == "passed"`（此时 `ensure()` 在后续转换点自动锚定变更前指纹）
4. 然后 `se_check_consistency(method="llm")` → 独立/自审语义审计 → `se_store_triage` 逐条裁定

### 存量发现处置（复用 triage）

| 裁决 | 语义 | 落点 |
|------|------|------|
| `accept_as_is` | 记为已知债务，不阻断 | proposals「legacy-debt」节：`\| id \| 描述 \| 裁决 \| 复查点 \|` |
| `defer` | 推迟，注明复查点（层/轮次） | 同上 + 复查点列 |
| `fix_impl` / `fix_design` | 属于本次变更范围内的真问题 | 走正常螺旋，不进债务清单 |

### 可见性（AC6 取舍）

v1：债务清单 = proposals「legacy-debt」节（人读 + agent 经 se_read_document 可见）；
不进 `se_get_project` 结构化输出（避免 schema 变更）。若实践发现"看不到债务"的问题，再升需求。

## 非目标（继承 L1）

- 不自动扫描导入现有代码；不做部分接管；子目录布局不自动配 code_root（保持手工，README 记录）

## 版本历史

| v0.23 | 2026-11-21 | 接管现有代码仓：Project.adopt + se_init_project(adopt_existing) + CLI --adopt-existing + work_mode 引导 + R40 摸底锚定契约 |
