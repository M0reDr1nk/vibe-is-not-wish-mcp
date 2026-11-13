---
created_at: '2026-11-13T10:02:21.465575'
layer: L2-参考文献与方案搜证汇总
se_version: '2.0'
updated_at: '2026-11-13T10:02:21.465575'
---

# 参考文献清单

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