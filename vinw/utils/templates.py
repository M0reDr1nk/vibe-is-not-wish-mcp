"""Markdown templates for SE-MCP v2 (spiral-ascend with evidence layer)."""

MANIFEST_TEMPLATE_V2 = """---
se_version: "2.0"
name: "{name}"
description: "{description}"
created_at: "{created_at}"
current_layer: "L1-需求拆解"
current_descent: 1
descent_started_at: "{created_at}"

layer_states:
  L1-需求拆解:
    status: "in_progress"
    latest_baseline: null
    descent_count: 1
  L2-参考文献与方案搜证汇总:
    status: "pending"
    latest_baseline: null
    descent_count: 0
  L3-方案细化:
    status: "pending"
    latest_baseline: null
    descent_count: 0
  L4-编码实现:
    status: "pending"
    latest_baseline: null
    descent_count: 0
  L5-测试验证:
    status: "pending"
    latest_baseline: null
    descent_count: 0
  L6-检视清理:
    status: "pending"
    latest_baseline: null
    descent_count: 0
  L7-终验:
    status: "pending"
    latest_baseline: null
    descent_count: 0

ascent_history: []
pending_confirmations: []
---

# 项目清单

| 字段 | 值 |
|------|-----|
| **项目名** | {name} |
| **描述** | {description} |
| **当前层** | L1-需求拆解 |
| **当前下降轮次** | descent-1 |

## 阶段速览

- [ ] L1 需求拆解
- [ ] L2 参考文献与方案搜证汇总
- [ ] L3 方案细化
- [ ] L4 编码实现
- [ ] L5 测试验证
- [ ] L6 检视清理
- [ ] L7 终验
"""

LAYER_README_TEMPLATE = """---
se_version: "2.0"
layer: "{layer}"
doc_type: "layer-readme"
status: "pending"
descent_count: 0
---

# {layer}

## 当前待办

- [ ] 初始化本层工作

## 阶段小结

（阶段完成时填写）

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| — | — | — |
"""

REFERENCES_TEMPLATE = """---
se_version: "2.0"
layer: "L2-参考文献与方案搜证汇总"
doc_type: "references"
updated_at: "{updated_at}"
---

# 参考文献清单

## 学术/技术文献

| 编号 | 标题 | 来源 | 日期 | 关键结论 | 关联度 |
|------|------|------|------|---------|--------|
| — | — | — | — | — | — |

## 开源/现有方案

| 编号 | 项目/产品 | 仓库/链接 | 核心机制 | 可复用点 | 风险/限制 |
|------|----------|----------|---------|---------|----------|
| — | — | — | — | — | — |

## 内部/历史方案

| 编号 | 来源项目 | 文档路径 | 关键决策 | 本次是否复用 |
|------|---------|---------|---------|------------|
| — | — | — | — | — |
"""

EVIDENCE_MATRIX_TEMPLATE = """---
se_version: "2.0"
layer: "L2-参考文献与方案搜证汇总"
doc_type: "evidence-matrix"
updated_at: "{updated_at}"
---

# 方案对比证据矩阵

## 候选方案

| 方案 | 核心思路 | 优势证据 | 劣势证据 | 关键风险 | 推荐度 |
|------|---------|---------|---------|---------|--------|
| — | — | — | — | — | — |

## 关键问题证据汇总

| 问题 | 证据来源 | 证据强度 | 结论 |
|------|---------|---------|------|
| — | — | — | — |
"""

SYNTHESIS_TEMPLATE = """---
se_version: "2.0"
layer: "L2-参考文献与方案搜证汇总"
doc_type: "synthesis"
updated_at: "{updated_at}"
---

# 搜证汇总结论

## 输入到 L3 的约束

1. （由证据矩阵推导的强制约束）

## 待 L3 决策的问题

- [ ] （待细化问题）

> 以上约束与待决策项将作为 L3 方案细化的强制输入。
"""

DESIGN_DOC_TEMPLATE = """---
se_version: "2.0"
layer: "L3-方案细化"
doc_type: "design-doc"
updated_at: "{updated_at}"
---

# 设计方案

## 设计约束（来自 L2）

（引用 L2/synthesis.md 中的约束）

## 架构决策

### 决策 1: xxx

- 备选方案:
- 选择理由:
- 拒绝理由:

## 数据模型

## 核心流程

## 变更记录

| 变更ID | 时间 | 内容 | 原因 |
|--------|------|------|------|
| — | — | — | — |
"""

API_DESIGN_TEMPLATE = """---
se_version: "2.0"
layer: "L3-方案细化"
doc_type: "api-design"
updated_at: "{updated_at}"
---

# 接口设计

## 接口清单

| 接口名 | 方法 | 路径 | 输入 | 输出 | 约束 |
|--------|------|------|------|------|------|
| — | — | — | — | — | — |

## 错误码

## 版本历史

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| — | — | — | — |
"""

IMPLEMENTATION_TEMPLATE = """---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "implementation"
updated_at: "{updated_at}"
---

# 实现笔记

## 关键代码决策

## 与设计文档的映射

| 设计文档段落 | 代码位置 | 实现状态 |
|-------------|---------|---------|
| — | — | — |

## 待解决问题

- [ ] —
"""

TEST_PLAN_TEMPLATE = """---
se_version: "2.0"
layer: "L5-测试验证"
doc_type: "test-plan"
updated_at: "{updated_at}"
---

# 测试计划

## 测试用例

| 编号 | 名称 | 类型 | 目标 | 预期结果 | 状态 |
|------|------|------|------|---------|------|
| — | — | — | — | — | 待执行 |

## 测试环境

## 通过标准
"""

TEST_RESULTS_TEMPLATE = """---
se_version: "2.0"
layer: "L5-测试验证"
doc_type: "test-results"
updated_at: "{updated_at}"
---

# 测试结果

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总用例 | 0 |
| 通过 | 0 |
| 失败 | 0 |
| 跳过 | 0 |

## 失败明细

| 用例编号 | 失败原因 | 关联 issue |
|---------|---------|-----------|
| — | — | — |

## 根因分析

（若发现设计级缺陷，记录上升回溯触发原因）
"""

DEBUG_SESSION_TEMPLATE = """---
se_version: "2.0"
layer: "L5-测试验证"
doc_type: "debug-session"
updated_at: "{updated_at}"
---

# 调试会话

## 问题描述

## 调试代码

```python
# 插入位置:
# 目的:
# 预期观察:
```

## 观察结果

## 结论
"""

CLEANUP_LOG_TEMPLATE = """---
se_version: "2.0"
layer: "L6-检视清理"
doc_type: "cleanup-log"
updated_at: "{updated_at}"
---

# 检视清理日志

## 清理操作

| 类型 | 位置 | 操作 | 原因 |
|------|------|------|------|
| — | — | — | — |

## 文档同步检查

- [ ] 设计文档与代码一致
- [ ] 接口文档与实现一致
- [ ] 变更日志完整

## 归档确认
"""

FINAL_REPORT_TEMPLATE = """---
se_version: "2.0"
layer: "L7-终验"
doc_type: "final-report"
updated_at: "{updated_at}"
---

# 终验报告

## 项目摘要

## 下降轮次统计

| 轮次 | 起始层 | 终止层 | 上升触发原因 | 关键变更 |
|------|--------|--------|-------------|---------|
| — | — | — | — | — |

## 基线清单

| 层 | 基线版本 | 冻结时间 |
|---|---------|---------|
| — | — | — |

## 遗留问题

## 归档位置
"""

ASCENSION_ENTRY_TEMPLATE = """
## {ascent_id} [{created_at}]

| 字段 | 内容 |
|------|------|
| **下降轮次前** | descent-{descent_before} |
| **来源层** | {from_layer} |
| **目标层** | {to_layer} |
| **目标基线** | {to_baseline} |
| **原因** | {reason} |
| **新下降轮次** | descent-{descent_after} |

> 上升后，{from_layer} 至 L7 的所有工作区标记为 superseded。
"""
