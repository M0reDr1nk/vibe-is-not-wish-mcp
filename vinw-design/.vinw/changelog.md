---
se_version: "2.0"
project: "se-mcp-self-design"
---

# 变更日志

## chg-20261113-100220-001 [2026-11-13T10:02:20.865851]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L1-需求拆解 |
| **范围** | `L1-需求拆解/v001` |
| **原因** | 需求拆解完成 |

### Before
```text

```

### After
```text

```

## chg-20261113-100221-002 [2026-11-13T10:02:21.167241]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-1 |
| **层** | L2-参考文献与方案搜证汇总 |
| **范围** | `L1-需求拆解→L2-参考文献与方案搜证汇总` |
| **原因** | Descend to L2-参考文献与方案搜证汇总 |

### Before
```text

```

### After
```text

```

## chg-20261113-100222-003 [2026-11-13T10:02:22.077333]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L2-参考文献与方案搜证汇总 |
| **范围** | `L2-参考文献与方案搜证汇总/v001` |
| **原因** | Evidence collection complete |

### Before
```text

```

### After
```text

```

## chg-20261113-100222-004 [2026-11-13T10:02:22.363961]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-1 |
| **层** | L3-方案细化 |
| **范围** | `L2-参考文献与方案搜证汇总→L3-方案细化` |
| **原因** | Descend to L3-方案细化 |

### Before
```text

```

### After
```text

```

## chg-20261113-100223-005 [2026-11-13T10:02:23.095293]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L3-方案细化 |
| **范围** | `L3-方案细化/v001` |
| **原因** | Design frozen — ready for implementation |

### Before
```text

```

### After
```text

```

## chg-20261113-101621-006 [2026-11-13T10:16:21.092814]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L3-方案细化 |
| **范围** | `L3-方案细化/v002` |
| **原因** | 遗留项决策完毕，design-doc/api-design/checkpoints 已更新 |

### Before
```text

```

### After
```text

```

## chg-20261113-101621-007 [2026-11-13T10:16:21.231818]

| 字段 | 内容 |
|------|------|
| **变更类型** | `design` |
| **下降轮次** | descent-1 |
| **层** | L3-方案细化 |
| **范围** | `design-doc.md + api-design.md + checkpoints.md` |
| **原因** | 遗留项决策：一致性检查=LLM文本审计+tree-sitter预留；向量检索=TF-IDF+rg |

### Before
```text
遗留项待决策
```

### After
```text
决策完毕，L3 重新基线化 v002
```

## chg-20261113-101621-008 [2026-11-13T10:16:21.569210]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-1 |
| **层** | L4-编码实现 |
| **范围** | `L3-方案细化→L4-编码实现` |
| **原因** | 设计冻结，进入编码实现阶段 |

### Before
```text

```

### After
```text

```

## chg-20261113-102200-009 [2026-11-13T10:22:00.550091]

| 字段 | 内容 |
|------|------|
| **变更类型** | `code` |
| **下降轮次** | descent-1 |
| **层** | L4-编码实现 |
| **范围** | `se_mcp/workflow/consistency_llm.py + search.py + server.py` |
| **原因** | 实现 se_check_consistency (LLM审计+text fallback) 和 se_search_proposals (rg+TF-IDF) |

### Before
```text
L4 待办：一致性检查和方案搜索未实现
```

### After
```text
LLMConsistencyAuditor + TextConsistencyChecker + ProposalSearcher 已实现并注册为 MCP tools
```

## chg-20261113-102417-010 [2026-11-13T10:24:17.294860]

| 字段 | 内容 |
|------|------|
| **变更类型** | `code` |
| **下降轮次** | descent-1 |
| **层** | L4-编码实现 |
| **范围** | `se_mcp/workflow/consistency_llm.py` |
| **原因** | 修复 text 检查器的表头误提取问题；添加已知限制说明 |

### Before
```text
text 检查器误报 20 条（表头提取+路径边界）
```

### After
```text
误报已分析并归档为已知限制，表头提取逻辑已优化
```

## chg-20261113-102418-011 [2026-11-13T10:24:18.068994]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L4-编码实现 |
| **范围** | `L4-编码实现/v001` |
| **原因** | L4 round 1 complete: consistency + search implemented |

### Before
```text

```

### After
```text

```

## chg-20261113-102418-012 [2026-11-13T10:24:18.366215]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-1 |
| **层** | L5-测试验证 |
| **范围** | `L4-编码实现→L5-测试验证` |
| **原因** | L4 complete, entering test validation |

### Before
```text

```

### After
```text

```

## chg-20261113-105021-013 [2026-11-13T10:50:21.455121+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `test` |
| **下降轮次** | descent-1 |
| **层** | L5-测试验证 |
| **范围** | `tests/ (36 cases)` |
| **原因** | L5 测试验证完成：36/36 通过，5 个 bug 修复，MCP tools + TUI 验证通过 |

### Before
```text
L5 待办：测试计划、单元测试、验证未执行
```

### After
```text
36 个单元测试全部通过，test-plan.md + test-results.md 已归档
```

## chg-20261113-105021-014 [2026-11-13T10:50:21.855592+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L5-测试验证 |
| **范围** | `L5-测试验证/v001` |
| **原因** | L5 round 1 complete: 36 tests passed, 5 bugs fixed |

### Before
```text

```

### After
```text

```

## chg-20261113-105022-015 [2026-11-13T10:50:22.163382+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-1 |
| **层** | L6-检视清理 |
| **范围** | `L5-测试验证→L6-检视清理` |
| **原因** | L5 complete, entering cleanup review |

### Before
```text

```

### After
```text

```

## chg-20261113-105525-016 [2026-11-13T10:55:25.502300+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `cleanup` |
| **下降轮次** | descent-1 |
| **层** | L6-检视清理 |
| **范围** | `se_mcp/` |
| **原因** | L6 检视清理完成：修复 frontmatter 缺失导入、移除废弃 consistency.py、统一 datetime.timezone、更新依赖与文档 |

### Before
```text
server.py 缺少 frontmatter 导入；consistency.py 已废弃；utcnow() DeprecationWarning 残留；README 缺少新工具说明
```

### After
```text
frontmatter 导入已添加；consistency.py 已删除；所有 utcnow() 已替换；README 已更新；pyproject.toml dev 依赖已补充 scikit-learn
```

## chg-20261113-105526-017 [2026-11-13T10:55:26.190875+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-1 |
| **层** | L6-检视清理 |
| **范围** | `L6-检视清理/v001` |
| **原因** | L6 round 1 complete: cleanup, bugfixes, docs updated |

### Before
```text

```

### After
```text

```

## chg-20261113-105526-018 [2026-11-13T10:55:26.479013+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-1 |
| **层** | L7-终验 |
| **范围** | `L6-检视清理→L7-终验` |
| **原因** | L6 complete, entering final verification |

### Before
```text

```

### After
```text

```

## chg-20261113-105633-019 [2026-11-13T10:56:33.121767+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `final` |
| **下降轮次** | descent-1 |
| **层** | L7-终验 |
| **范围** | `se-mcp v0.2.0` |
| **原因** | L7 终验完成：descent-1 全部 7 层通过，36 测试通过，项目可交付 |

### Before
```text
descent-1 进行中
```

### After
```text
descent-1 完成：L1-L7 全部 baselined，终验报告已归档
```

## chg-20261113-153045-020 [2026-11-13T15:30:45.035158+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `feature` |
| **下降轮次** | descent-1 |
| **层** | L7-终验 |
| **范围** | `vinw/server.py: se_init_project, _try_load_bootstrap_project` |
| **原因** | 自举改造：支持加载/接管已有 VINW 工程（代码已于 L7 状态下提前落地，此处补记变更日志） |

### Before
```text
se_init_project 仅支持空目录初始化；server 无活动工程时所有工具报 "No active project"
```

### After
```text
se_init_project 支持接管已有工程；server 启动时自动加载 cwd/vinw-design 或 cwd 下的 .se/manifest.md 作为活动工程
```

## chg-20261113-153050-021 [2026-11-13T15:30:50.527978+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `ascend` |
| **下降轮次** | descent-2 |
| **层** | L3-方案细化 |
| **范围** | `L7-终验→L3-方案细化(v002)` |
| **原因** | [asc-001] 新增自举能力（se_init_project 接管已有工程 + 启动自动加载），需更新 L3 接口设计后重新下降实现 |

### Before
```text
descent-1 @ L7-终验
```

### After
```text
descent-2 @ L3-方案细化
```

## chg-20261113-153454-022 [2026-11-13T15:34:54.278927+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `bugfix` |
| **下降轮次** | descent-2 |
| **层** | L3-方案细化 |
| **范围** | `vinw/workflow/consistency_llm.py: _resolve_code_root, _collect_code_files; vinw-design/.se/manifest.md: code_root` |
| **原因** | 一致性检查在自举场景下误报 20 个符号全部缺失：修复代码定位规则（L3 v0.3 设计已同步修订） |

### Before
```text
代码根固定为项目根；code_scope 仅支持目录（文件条目 rglob 空结果）；无排除目录机制
```

### After
```text
manifest.code_root 支持（自举场景 ".."）；code_scope 支持文件/目录混合；排除 .venv/build/node_modules 等目录
```

## chg-20261113-154330-023 [2026-11-13T15:43:30.370990+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `refactor` |
| **下降轮次** | descent-2 |
| **层** | L3-方案细化 |
| **范围** | `vinw/store/project.py, vinw/server.py, tests/, scripts/, README.md, vinw-plugin/` |
| **原因** | 门控 modify 反馈：.se 统一更名 .vinw（设计 v0.3 已修订，45/45 测试通过，MCP 自举实测加载成功） |

### Before
```text
状态目录为 .se/（Project.se_dir）
```

### After
```text
状态目录统一为 .vinw/（Project.vinw_dir）；全仓代码/文档/插件/脚本适配；vinw-design/.se 已移动为 vinw-design/.vinw
```

## chg-20261113-154339-024 [2026-11-13T15:43:39.453863+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-2 |
| **层** | L3-方案细化 |
| **范围** | `L3-方案细化/v003` |
| **原因** | descent-2 L3 接口设计 v0.3 定稿（自举加载 + 一致性代码定位规则 + .vinw 更名），门控 modify 通过 |

### Before
```text

```

### After
```text

```

## chg-20261113-154342-025 [2026-11-13T15:43:42.728047+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-2 |
| **层** | L4-编码实现 |
| **范围** | `L3-方案细化→L4-编码实现` |
| **原因** | L3 v003 已定稿，下降进入编码实现 |

### Before
```text

```

### After
```text

```

## chg-20261113-154422-026 [2026-11-13T15:44:22.630876+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-2 |
| **层** | L4-编码实现 |
| **范围** | `L4-编码实现/v002` |
| **原因** | descent-2 L4：自举 + 一致性定位 + .vinw 更名完成，一致性检查 20/20 passed（report-c88f12f4） |

### Before
```text

```

### After
```text

```

## chg-20261113-154425-027 [2026-11-13T15:44:25.613437+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-2 |
| **层** | L5-测试验证 |
| **范围** | `L4-编码实现→L5-测试验证` |
| **原因** | L4 v002 已定稿，下降进入测试验证 |

### Before
```text

```

### After
```text

```

## chg-20261113-154459-028 [2026-11-13T15:44:59.653547+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-2 |
| **层** | L5-测试验证 |
| **范围** | `L5-测试验证/v002` |
| **原因** | descent-2 L5：45/45 通过，测试结果已录入（门控 cfm-...-002 为非阻塞，供用户 review） |

### Before
```text

```

### After
```text

```

## chg-20261113-154502-029 [2026-11-13T15:45:02.464470+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-2 |
| **层** | L6-检视清理 |
| **范围** | `L5-测试验证→L6-检视清理` |
| **原因** | L5 v002 已定稿，下降进入检视清理 |

### Before
```text

```

### After
```text

```

## chg-20261113-154537-030 [2026-11-13T15:45:37.638580+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `baseline` |
| **下降轮次** | descent-2 |
| **层** | L6-检视清理 |
| **范围** | `L6-检视清理/v002` |
| **原因** | descent-2 L6：废弃产物/缓存/跟踪文件清理完成，文档同步，45/45 复验通过 |

### Before
```text

```

### After
```text

```

## chg-20261113-154540-031 [2026-11-13T15:45:40.911328+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `descend` |
| **下降轮次** | descent-2 |
| **层** | L7-终验 |
| **范围** | `L6-检视清理→L7-终验` |
| **原因** | L6 v002 已定稿，下降进入终验 |

### Before
```text

```

### After
```text

```

## chg-20261113-160113-032 [2026-11-13T16:01:13.289420+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `bugfix` |
| **下降轮次** | descent-2 |
| **层** | L7-终验 |
| **范围** | `vinw/tui/app.py: refresh_ui 顶部面板` |
| **原因** | 用户实际运行 TUI 报错：TypeError: unsupported operand type(s) for +: 'Columns' and 'Text'（app.py 层状态图面板渲染，descent-1 漏测：仅验证启动未验证渲染） |

### Before
```text
Columns + Text 直接相加，rich Columns 不支持 __add__
```

### After
```text
使用 rich.console.Group 垂直组合 Columns/Text/Panel
```

## chg-20261113-160702-033 [2026-11-13T16:07:02.696626+00:00]

| 字段 | 内容 |
|------|------|
| **变更类型** | `bugfix` |
| **下降轮次** | descent-2 |
| **层** | L7-终验 |
| **范围** | `vinw/server.py: se_update_todo; vinw/store/project.py: get_todos; vinw-design/L1~L3 README` |
| **原因** | 用户排查待办状态未更新：模板占位符从未通过 se_update_todo 维护 + 轮次标记失真 |

### Before
```text
get_todos 对所有待办打当前轮次，descent-1 遗留待办显示为 descent-2；L1/L2/L3 待办停留在未勾选模板占位符
```

### After
```text
se_update_todo 写入 todo_descent frontmatter；get_todos 优先读取写入轮次；L1/L2/L3 待办已按真实完成状态修正
```
