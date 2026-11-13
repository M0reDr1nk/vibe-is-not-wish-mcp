#!/usr/bin/env python3
"""Populate SE-MCP self-design documentation into a project instance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vinw.store.project import Project
from vinw.workflow.state_machine import WorkflowEngine

ROOT = Path("/mnt/agents/output/vinw-design")

if ROOT.exists():
    import shutil
    shutil.rmtree(ROOT)

proj = Project.init(ROOT, "vinw-self-design", "SE-MCP v2 self-design documentation")
engine = WorkflowEngine(proj)

# ── L1: 需求拆解 ───────────────────────────────────────────

proj.write_document("L1-需求拆解", "proposals.md", """# 需求拆解

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
""")

engine.baseline("L1-需求拆解", "需求拆解完成")
engine.descend("L2-参考文献与方案搜证汇总")

# ── L2: 参考文献与方案搜证汇总 ─────────────────────────────

proj.write_document("L2-参考文献与方案搜证汇总", "references.md", """# 参考文献清单

## 技术规范

| 编号 | 标题 | 来源 | 关键结论 | 关联度 |
|------|------|------|---------|--------|
| ref-001 | Model Context Protocol (MCP) | modelcontextprotocol.io | 通用 agent 能力扩展协议，跨 harness 标准 | 高 |
| ref-002 | MCP Python SDK v2.x | github.com/modelcontextprotocol/python-sdk | MCPServer 替代 FastMCP，API 变更 | 高 |
| ref-003 | Textual (Python TUI) | textual.textualize.io | 现代 Python TUI 框架，rich 渲染 | 高 |

## 现有方案对比

| 编号 | 项目 | 核心机制 | 可复用点 | 风险/限制 |
|------|------|---------|---------|----------|
| oss-001 | Aider | diff-based 代码编辑 | 编辑粒度控制 | 缺乏过程门控、无归档 |
| oss-002 | Devin / OpenHands | 全自动 agent | 端到端能力 | 缺少用户确认硬约束、无变更原子日志 |
| oss-003 | Cursor Composer | IDE 内 agent | 上下文感知 | 绑定 IDE，不可跨 harness |
| oss-004 | GitHub Copilot Workspace | PR 级工作流 | 任务分解 | 绑定 GitHub，不可跨 harness |

## 关键问题证据

| 问题 | 证据来源 | 证据强度 | 结论 |
|------|---------|---------|------|
| 跨 harness 可行性 | MCP 协议文档 + 多客户端测试 | 强 | MCP 是唯一跨 harness 通用协议 |
| Markdown 分层存储可行性 | Git 工作流类比 + 文件系统特性 | 强 | 适合 <1000 文件的软件工程项目 |
| 螺旋上升 vs 线性 | 软件工程实践（螺旋模型） | 中 | 显式回溯优于线性推进 |
| TUI 实时刷新可行性 | Textual 文档 + set_interval | 强 | 2 秒轮询重读文件系统完全可行 |
""")

proj.write_document("L2-参考文献与方案搜证汇总", "evidence-matrix.md", """# 方案对比证据矩阵

## 层级选择

| 方案 | 核心思路 | 优势 | 劣势 | 推荐度 |
|------|---------|------|------|--------|
| A. 纯 Skill | SKILL.md 工作流协议 | 强工作流编排 | 绑定特定 harness，不可跨 | ⭐⭐ |
| B. 纯 MCP | MCPServer 工具集 | 跨 harness | 无工作流指导，agent 不知道何时调用 | ⭐⭐⭐ |
| C. 纯 Agent | 自主 agent | 自主决策 | 无通用编排框架，不可跨 | ⭐⭐ |
| **D. MCP + Skill** | MCP 能力底座 + Skill 工作流协议 | 跨 harness + 工作流指导 | 需要两套实现 | **⭐⭐⭐⭐⭐** |

## 存储层选择

| 方案 | 核心思路 | 优势 | 劣势 | 推荐度 |
|------|---------|------|------|--------|
| A. SQLite | 结构化查询 | SQL 强大、事务安全 | 不可读、需导出工具 | ⭐⭐ |
| **B. Markdown 分层** | 文件系统 + frontmatter | 人类可读、git 友好、跨工具 | 查询弱、无事务 | **⭐⭐⭐⭐⭐** |
| C. 混合 | Markdown + SQLite 索引 | 兼顾可读与查询 | 复杂度翻倍、同步风险 | ⭐⭐⭐ |

## 状态机设计

| 方案 | 核心思路 | 优势 | 劣势 | 推荐度 |
|------|---------|------|------|--------|
| A. 线性 6/7 phase | 一次性经过 | 简单直观 | 无法回溯上升 | ⭐⭐ |
| **B. 螺旋上升分层图** | 上升-基线恢复-再下降 | 显式回滚、轮次可追溯 | 状态复杂度高 | **⭐⭐⭐⭐⭐** |

## 关键问题证据汇总

| 问题 | 证据强度 | 结论 |
|------|---------|------|
| 必须显式基线冻结 | 强 | 基线是回滚锚点，不可省略 |
| 必须显式上升记录 | 强 | 每次上升必须在 ascensions.md 留下不可变记录 |
| 变更日志必须前置 | 强 | se_log_change 必须在实际修改前调用 |
| 门控必须阻塞性 | 强 | se_require_confirmation 的 blocking 不可绕过 |
""")

proj.write_document("L2-参考文献与方案搜证汇总", "synthesis.md", """# 搜证汇总结论

## 输入到 L3 的强制约束

1. **必须采用 MCP + Skill 双层架构**（证据：层级选择矩阵方案 D）
   - MCP Server 提供跨 harness 的确定性能力（18 个工具）
   - Skill（SKILL.md）在支持的环境中约束 agent 行为模式

2. **必须采用 Markdown 分层存储**（证据：存储层矩阵方案 B）
   - 每个项目是一个自包含的目录树
   - 目录名即状态机阶段编号
   - 人类可随时 cat/vim/diff

3. **必须采用螺旋上升状态机**（证据：状态机矩阵方案 B）
   - 7 层结构：L1→L2→L3→L4→L5→L6→L7
   - 上升：从当前层到更上层的指定基线（触发新下降轮次）
   - 下降：从当前层到更下层（需中间层已基线化）
   - 基线：每层完成时显式冻结快照

4. **必须显式记录-回滚**（证据：关键问题证据汇总）
   - 上升操作 = 被记录的变更（写入 changelog + ascensions）
   - 下层标记 superseded 而非删除（保留痕迹）
   - descent_count 记录每层被多少次下降轮次触及

5. **TUI 必须实时刷新**（证据：Textual 可行性）
   - set_interval(2, refresh_ui) 轮询文件系统
   - 纯只读，所有修改通过 MCP tools

## 待 L3 决策的问题

- [ ] 一致性检查深度：文本比对 vs tree-sitter AST 结构化比对
- [ ] 基线粒度：单文件（README）vs 整层目录所有文档
- [ ] 向量检索：是否需要 faiss 用于近似方案搜集
- [ ] 部署形式：pip install 后 vinw server 启动 vs Kimi plugin 包
""")

engine.baseline("L2-参考文献与方案搜证汇总", "Evidence collection complete")
engine.descend("L3-方案细化")

# ── L3: 方案细化 ───────────────────────────────────────────

proj.write_document("L3-方案细化", "design-doc.md", """# SE-MCP v2 设计方案

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

## 技术栈

| 层 | 库/工具 |
|----|---------|
| MCP Server | `mcp` (Python SDK v2.x, MCPServer) |
| 文件存储 | `pathlib` + `python-frontmatter` |
| TUI 渲染 | `textual` + `rich` |
| 语法解析 | `tree-sitter` (预留) |
| 向量检索 | `faiss-cpu` (预留) |

## 变更记录

| 变更ID | 时间 | 内容 | 原因 |
|--------|------|------|------|
| chg-001 | 2026-11-13 | 增加 L2 证据层 | 需求：显式参考文献搜证阶段 |
| chg-002 | 2026-11-13 | 线性状态机 → 螺旋上升 | 需求：显式回溯-再下降循环 |
""")

proj.write_document("L3-方案细化", "api-design.md", """# 接口设计

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
| `se_check_consistency` | design_layer, design_doc, code_scope | matched, inconsistencies, overall |

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
""")

proj.write_document("L3-方案细化", "checkpoints.md", """# 设计约束与检查点

- [x] 架构决策已记录（MCP + Skill + Markdown 分层）
- [x] 接口签名已冻结（18 个 MCP tools）
- [x] 数据模型已确认（7 层目录 + manifest 状态机）
- [x] 螺旋上升机制已设计（ascend/descend/baseline 三操作）
- [x] 门控机制已设计（require/resolve confirmation）
- [x] TUI 可视化已设计（3 面板实时刷新）
- [ ] 一致性检查深度待决策（文本比对 vs AST）
- [ ] 向量检索待决策（是否需要 faiss）
""")

engine.baseline("L3-方案细化", "Design frozen — ready for implementation")

print("=" * 60)
print("SE-MCP self-design documentation populated successfully")
print("=" * 60)
print(f"Project path: {proj.root}")
print(f"Current layer: {proj.get_current_layer()}")

manifest = proj.read_manifest()
print(f"Descent: {manifest['current_descent']}")
print(f"Baselines:")
for layer in ["L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化"]:
    print(f"  {layer}: {proj.list_baselines(layer)}")

print(f"\nDocuments created:")
for layer in ["L1-需求拆解", "L2-参考文献与方案搜证汇总", "L3-方案细化"]:
    files = [f.name for f in proj.get_layer_dir(layer).glob("*.md") if f.name != "README.md"]
    print(f"  {layer}: {files}")
