---
created_at: '2026-11-13T10:02:21.735110'
layer: L2-参考文献与方案搜证汇总
se_version: '2.0'
updated_at: '2026-11-13T10:02:21.735110'
---

# 搜证汇总结论

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
- [ ] 部署形式：pip install 后 se-mcp server 启动 vs Kimi plugin 包
---

# descent-7 结论与推荐方向（供 L3 设计）

## 结论 1：注册表 = `~/.vinw/registry.json`

- 结构：`{"version": 1, "projects": {"<abs-path>": {"name": ..., "added_at": ..., "last_accessed_at": ..., "last_seen_ok": ..., "missing_since": ...}}}`
- 写入：`tmp` + `os.replace` 原子替换；读多写少，无需锁文件（写入前重读合并）
- 位置可用 `VINW_HOME` 环境变量覆盖（便于测试与多环境隔离）
- **否决 SQLite 的理由已记录在证据矩阵**

## 结论 2：失效工程 = 探测标记 + 显式 prune

- `status: ok`（`.vinw/manifest.md` 存在）或 `status: missing`
- `missing` 条目不自动删除；`prune` 默认 `--dry-run`，需 `--force` 才真删
- `missing_since` 记录首次发现缺失时间，便于用户判断

## 结论 3：寻址 = 路径主键 + 名称别名

- MCP `project` 参数接受：绝对/相对路径、注册名、`null`
- 解析顺序：路径存在→解析为路径；否则查注册表名；仍无→结构化错误

## 结论 4：向后兼容红线

- 所有 `se_*` 工具 `project` 参数**可选**，省略时走现有自举 + 单例逻辑
- `vinw tui <path>` 现有用法不变；无参时进入选择器

## 结论 5：TUI 交互

- 顶部 header 常显：`工作目录: <cwd>` 与 `当前工程: <name> @ <path>`
- 无参启动 → 选择器（注册工程 + cwd 探测工程，键盘上下 + Enter）
- 快捷键 `p` 打开切换器（任意时刻），`r` 刷新，`q` 退出
