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

---

# descent-8 选型复核与更正（asc-007）

## 触发

用户质疑「txt 类总体记录管理不靠谱」，并指出：**全局注册表只是状态切换记录，没有可读内容价值；工程内部才需要 Markdown 可读呈现**。

## 更正声明（重要：记录此前的判断错误）

descent-7 的决策 A 得出「JSON 13/14 分、SQLite 5/14 分」，但该矩阵存在**权重错配**：

| 出错项 | 原判断 | 更正 |
|--------|--------|------|
| 「人类可读 / git diff」权重 3 | 给 JSON 3 分、SQLite 0 分 | **该准则对注册表不适用**：注册表是 per-machine 运行状态，不进 git、不需人工 review；把它当设计产物评分是对象错配 |
| 「规模不够所以不需要 SQLite」 | 5–500 项目 < SQLite 优势区间 | **看错了轴**：决定性因素是并发写、写放大、崩溃一致性，不是数据量 |
| 「SQLite 实现复杂度高」 | 扣分 | 反面：JSON 方案要自己实现锁/事务/并发合并，等价于手搓数据库且更容易出错 |

实测证据（300 条登记）：

| 操作 | JSON 方案实测 | SQLite 方案 |
|------|--------------|------------|
| `list()` 全量探测 | 14.5 ms（首次 1 次全表重写） | 单次查询 + 按需探测 |
| 每次带 `project` 的工具调用 | `touch()` 整表读+整表重写，9.5 ms/次 | 单行 UPDATE，微秒级 |
| 并发写保护 | 无锁，仅「写前重读 + 原子替换」→ 可丢更新 | WAL + 事务 + busy_timeout |
| diff 噪音（单字段改动/20 条） | 2 行 | — |

补充实测：JSON / CSV / JSONL 三者对单字段修改的 **diff 噪音相同（均 2 行）**，故「JSON 更适合 git」在本数据形状下本就不成立，CSV 只是更紧凑（1944 B vs 4598 B）。

## 结论：控制面 / 数据面分层

| | 控制面（全局注册表） | 数据面（工程内文档） |
|---|---|---|
| 载体 | **SQLite**（`$VINW_HOME/registry.db`） | **Markdown + frontmatter**（`<工程>/.vinw/*.md`） |
| 写入者 | 程序，高频自动 | 人 + agent，低频深思 |
| 并发 | MCP server + TUI + CLI 三进程 → 需锁与事务 | 单写者，顺序 |
| 进 git | 否（per-machine） | 是（过程即产物） |
| 可读性诉求 | 低（用 `vinw project list` 读） | 高（review / diff / 归档） |

## CSV 方案再评估（回应用户提议）

CSV 对本 schema 结构性够用（全标量、1966 B 最紧凑），但：
1. null 与空串无法区分（`missing_since: null` vs `""`）
2. Excel/Numbers 编辑会篡改（ISO 日期本地化、`=` 开头路径变公式）
3. 无嵌套能力，schema 演进受限
4. **同样没有并发锁**——与 JSON 共享最大缺陷

→ 若「需要人用表格软件编辑」则 CSV 合理；本场景不需要（注册表不进 git、不需人工编辑），故选 SQLite。

## 遗留待 L3 决定

- 是否保留 JSON 导出（建议保留：`vinw project export` 供人查看/备份）
- 状态切换是否留痕（建议新增 `project_events` 表，支持 `vinw project history`）
