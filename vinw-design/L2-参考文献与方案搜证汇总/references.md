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
---

# descent-7 搜证：多项目注册表与失效清理（asc-006）

## 同类工具的做法

| 工具 | 注册表机制 | 失效处理 | 可借鉴点 |
|------|-----------|---------|---------|
| **git**（`git worktree list` 类比） | 无中心注册表，靠文件系统发现 | — | 发现式优于注册式 |
| **tmux / screen** | 运行时 socket + session 列表 | 进程退出即清理 | 生命周期与进程绑定 |
| **docker** | 本地 daemon 状态库（SQLite/BoltDB） | `docker system prune` 显式清理 | **标记 + 显式 prune**，不自动删 |
| **poetry / pipx / nvm** | 目录扫描（`~/.local/pipx/venvs`） | 目录不存在即视为不存在 | 文件系统即真相 |
| **VS Code / JetBrains** | 最近项目列表（JSON） | 打开失败时提示并从列表移除 | **JSON + 打开时校验** |
| **kubectl contexts** | `~/.kube/config` YAML 多上下文 | 集群不可达时报错不删除 | 单文件多条目 + 命名寻址 |
| **pre-commit** | 存 config 于仓库内 | — | 仓内配置 |

## 关键结论（支撑 L3 选型）

1. **主流工具几乎都用 JSON/YAML 单文件 + 显式清理**，SQLite 多见于有 daemon 的场景（docker、systemd）
2. **没有工具会静默删除用户在注册表里的条目**——普遍是「标记不可用 + 用户显式 prune」
3. **文件系统即真相**：判断工程有效性只需探测 `<root>/.vinw/manifest.md`，无需额外元数据
4. **单文件多条目 + 命名寻址**（kubectl 风格）比"一个文件一个工程"更贴合本场景

## 规模估算（决定选型）

| 场景 | 项目数 | 每次操作读写量 | 并发写者 |
|------|--------|--------------|---------|
| 个人本地 | 5–50 | < 10KB | MCP server 1 个 + TUI 1 个（偶发） |
| 团队共享盘 | 50–500 | ~100KB | 多个 harness 进程 |

结论：**规模远低于需要 SQLite 的阈值**（SQLite 优势在数千行以上 + 高频事务）。
