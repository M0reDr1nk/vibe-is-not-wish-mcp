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