---
name: vinw-workflow
description: >
  当用户需要执行严格的软件工程流程时使用此技能：需求拆解→文献搜证→方案细化→编码实现→测试验证→检视清理→终验。
  关键词触发："启动 VINW 项目"、"按工作流开发"、"螺旋上升"、"基线化"、"上升回溯"、
  "一致性检查"、"确认门控"、"变更日志"、"软件工程过程控制"。
  该技能指导 agent 使用原生文件工具管理 Markdown 项目结构，执行 7 层螺旋工作流。
---

# VINW 螺旋上升软件工程工作流

## 何时使用此技能

当用户表达以下意图时激活：
- "帮我做一个项目，要严格按流程来"
- "用 VINW 工作流开发 XXX"
- "启动螺旋上升项目"
- "需要基线冻结和上升回溯"
- "按软件工程规范实现功能"
- 任何涉及多阶段开发且需要过程控制的场景

## 项目初始化

### 1. 创建项目目录结构

在项目根目录下创建以下结构：

```
<project-name>/
├── .vinw/
│   ├── manifest.md          # 全局状态机
│   ├── changelog.md         # 原子变更日志
│   ├── ascensions.md        # 上升历史
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
│   ├── code-map.md
│   └── .baseline/
├── L5-测试验证/
│   ├── README.md
│   ├── test-plan.md
│   └── test-results.md
├── L6-检视清理/
│   └── README.md
└── L7-终验/
    └── README.md
```

### 2. manifest.md 模板

```yaml
---
se_version: "2.0"
name: <project-name>
description: <project-description>
created_at: <ISO8601>
current_layer: L1-需求拆解
current_descent: 1
status: in_progress
layer_states:
  L1-需求拆解:
    status: in_progress
    descent_count: 1
  L2-参考文献与方案搜证汇总:
    status: pending
    descent_count: 0
  L3-方案细化:
    status: pending
    descent_count: 0
  L4-编码实现:
    status: pending
    descent_count: 0
  L5-测试验证:
    status: pending
    descent_count: 0
  L6-检视清理:
    status: pending
    descent_count: 0
  L7-终验:
    status: pending
    descent_count: 0
pending_confirmations: []
ascent_history: []
---
```

### 3. 每层 README.md 模板

每层 README.md 必须包含：
- YAML frontmatter: `se_version`, `layer`, `doc_type: layer-readme`, `status`, `descent_count`
- 当前待办 (使用 `- [ ]` / `- [x]` 格式)
- 阶段小结区域 (完成时填写)
- 基线记录表格

## 工作流执行规则

### 规则 1：绝不跳过层

必须从 L1 开始，逐层下降。L(n) 未完成基线化前，不得进入 L(n+1)。

### 规则 2：基线冻结 (Baseline)

每层完成时：
1. 将该层 README.md 复制到 `.baseline/v{NNN}.md`
2. 更新 manifest 中该层状态为 `baselined`
3. 记录基线版本号和时间戳

### 规则 3：上升回溯 (Ascend)

当发现当前层无法解决的问题（根因在上层）时：
1. 向用户说明问题根因和建议上升到的目标层
2. 获得用户确认后，执行上升：
   - 记录上升记录到 `.vinw/ascensions.md`
   - 将当前层及下方所有层标记为 `superseded`
   - 回滚目标层到指定基线版本
   - 创建新的 descent 轮次 (descent_count + 1)
   - 从目标层重新开始

### 规则 4：确认门控 (Confirmation Gate)

以下场景必须插入阻塞性人工确认：

| 场景 | 确认内容 |
|------|---------|
| L1→L2 下降前 | 需求拆解结论是否准确完整 |
| L2→L3 下降前 | 文献搜证和方案推荐是否可靠 |
| L3→L4 下降前 | 接口设计方案是否通过评审 |
| L4→L5 下降前 | 编码实现与设计文档是否一致 |
| L5 测试发现设计缺陷 | 是否执行上升回溯 |
| L5→L6 下降前 | 测试结果是否通过 |
| L6→L7 下降前 | 检视清理是否完成 |
| L7 终验前 | 项目是否达到可交付状态 |

确认项格式：
```markdown
## 确认项 [cfm-{timestamp}-{seq}]

| 字段 | 内容 |
|------|------|
| 类型 | gate / design / test / final |
| 描述 | {具体确认内容} |
| 选项 | approve / reject / modify |
| 阻塞性 | true |
| 提出时间 | {ISO8601} |

### 用户决议
[待填写]
```

确认未解析前，禁止执行下降操作。

### 规则 5：变更原子记录

每次修改文件前，必须在 `.vinw/changelog.md` 追加记录：

```markdown
## chg-{timestamp}-{seq}

| 字段 | 内容 |
|------|------|
| 变更类型 | code / test / doc / cleanup / design |
| 下降轮次 | descent-{N} |
| 层 | L{N}-{name} |
| 范围 | {文件或模块} |
| 原因 | {为什么做这次变更} |

### Before
```text
{修改前的状态}
```

### After
```text
{修改后的状态}
```
```

### 规则 6：一致性检查

L4 编码实现阶段，必须定期进行设计-代码一致性检查：

**Text 方法（无 LLM 时）**：
1. 从 design-doc.md / api-design.md 提取所有函数名、类名、接口名
2. 在代码目录中搜索这些符号的存在性
3. 记录未找到的符号为 WARNING

**LLM 方法（推荐）**：
1. 将 design-doc.md + 代码全文构造为结构化 prompt
2. 要求 LLM 返回 JSON 格式的一致性报告
3. 报告包含：matched / inconsistencies / overall 字段
4. 将报告存储到 `L4-编码实现/consistency-reports/report-{id}.md`

### 规则 7：Todo 管理

每层 README.md 的 `## 当前待办` 章节使用标准 markdown checklist：

```markdown
## 当前待办

- [ ] 任务 A
- [x] 任务 B (已完成)
```

完成后更新对应 checkbox。跨层扫描时，汇总所有非 superseded 层的待办。

## 各层工作指南

### L1-需求拆解

**目标**：将用户意图拆解为可验证的原子需求

**输出文件**：
- `proposals.md` — 需求提案列表，每条包含：需求描述、验收标准、优先级

**完成标准**：
- [ ] 所有需求项有明确的验收标准
- [ ] 需求间无冲突
- [ ] 用户确认需求拆解准确

**下降动作**：基线化 L1 → 确认门控 → 下降到 L2

### L2-参考文献与方案搜证汇总

**目标**：搜集现有方案、文献、竞品，为设计决策提供证据

**输出文件**：
- `references.md` — 参考文献和方案链接
- `evidence-matrix.md` — 证据矩阵（方案 × 评估维度）
- `synthesis.md` — 综合结论和推荐选型

**完成标准**：
- [ ] 至少 3 个相关方案或文献被评估
- [ ] 证据矩阵覆盖关键评估维度
- [ ] 推荐选型有明确理由
- [ ] 用户确认推荐方向

**下降动作**：基线化 L2 → 确认门控 → 下降到 L3

### L3-方案细化

**目标**：基于 L2 综合结论，细化接口和实现方案

**输出文件**：
- `design-doc.md` — 架构设计文档
- `api-design.md` — 接口设计文档（含函数签名、参数、返回值）
- `code-map.md` — 代码-设计映射表（设计符号 → 代码位置）

**完成标准**：
- [ ] 架构设计文档完整
- [ ] 接口设计文档含完整签名
- [ ] 代码映射表已建立
- [ ] 用户确认接口设计

**下降动作**：基线化 L3 → 确认门控 → 下降到 L4

### L4-编码实现

**目标**：严格按设计文档实现代码

**关键规则**：
1. 每实现一个模块前，检查 design-doc.md 对应部分
2. 每次修改前记录变更日志
3. 编码完成后执行一致性检查

**输出文件**：
- `implementation.md` — 实现笔记和决策记录
- `consistency-reports/report-{id}.md` — 一致性检查报告

**完成标准**：
- [ ] 所有设计符号在代码中有对应实现
- [ ] 一致性检查通过（或已知限制已记录）
- [ ] 代码风格统一

**下降动作**：基线化 L4 → 确认门控 → 下降到 L5

### L5-测试验证

**目标**：验证实现正确性，发现设计级缺陷

**输出文件**：
- `test-plan.md` — 测试计划
- `test-results.md` — 测试结果

**完成标准**：
- [ ] 测试计划覆盖核心路径
- [ ] 所有测试用例执行完毕
- [ ] 结果已记录

**特殊处理**：
- 若发现设计级缺陷，必须执行上升回溯，不得在当前层绕过
- 向用户说明缺陷根因和建议上升到的目标层

**下降动作**：基线化 L5 → 确认门控 → 下降到 L6（或通过上升回到上层）

### L6-检视清理

**目标**：移除调试代码、废弃注释，统一风格，同步文档

**检查清单**：
- [ ] 无遗留调试 print/debugger
- [ ] 无 TODO/FIXME 未处理（或已转 issue）
- [ ] 代码风格统一（PEP8、类型注解等）
- [ ] 文档与代码同步
- [ ] 依赖项清理

**下降动作**：基线化 L6 → 确认门控 → 下降到 L7

### L7-终验

**目标**：项目归档，生成终验报告

**输出文件**：
- `final-report.md` — 终验报告

**报告内容**：
- 项目基本信息
- 各层完成状态与基线记录
- 功能实现清单
- 测试覆盖总结
- 已知限制
- 结论

**完成标准**：
- [ ] 终验报告完整
- [ ] 项目标记为 completed

## 安全与约束

### 禁止行为
- 擅自修改已基线化的层（除非执行上升）
- 跳过未解析的确认门控
- 将"感觉对了"当作工程判断依据
- 发现不一致时偷偷改代码而不记录
- 上升时不记录原因和目标基线

### 鼓励行为
- 频繁基线化（小步快跑）
- 详细记录变更意图（before/after）
- 主动提出上升回溯建议（当发现设计缺陷时）
- 在文档中明确标注已知限制
- 使用户始终了解当前所在的层和 descent 轮次

## 与 VINW MCP Server 的关系

此技能是 VINW 工作流的方法论层。当用户同时运行了本地 VINW MCP Server（`vinw server --http`）时：
- 优先使用 MCP tools 执行状态机操作（基线化、上升、下降、确认门控）
- MCP Server 会自动管理 manifest 状态和变更日志
- 此技能提供工作流指导和规则约束

当 MCP Server 不可用时，此技能指导你使用原生文件工具手动管理项目结构，保持同样的严格性。
