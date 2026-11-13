---
se_version: "2.0"
layer: "L7-终验"
doc_type: "final-report"
status: "in_progress"
---

# 终验报告 — VINW（descent-6，最终版）

## 项目信息

| 字段 | 值 |
|------|-----|
| 项目名称 | vinw-self-design |
| 下降轮次 | descent-1 ~ descent-6 |
| 上升次数 | 5（asc-001 ~ asc-005） |
| 终验时间 | 2026-11-13 |
| 版本 | 0.2.0 |

## 各层完成状态

| 层 | 状态 | 基线 | 下降次数 |
|---|------|------|---------|
| L1-需求拆解 | ✅ baselined | v001 | 1 |
| L2-参考文献与方案搜证汇总 | ✅ baselined | v001 | 1 |
| L3-方案细化 | ✅ baselined | v001–v007, **v008** | 6 |
| L4-编码实现 | ✅ baselined | v001–v005, **v006** | 6 |
| L5-测试验证 | ✅ baselined | v001–v005, **v006** | 6 |
| L6-检视清理 | ✅ baselined | v001–v005, **v006** | 6 |
| L7-终验 | ✅ completed | — | 6 |

## 上升记录（ascensions.md）

| ID | 路径 | 原因 |
|----|------|------|
| asc-001 | L7 → L3(v002) | 新增自举能力，需更新 L3 接口设计 |
| asc-002 | L7 → L3(v003) | descent-2 终验后三项热修未走流程，补救上升 |
| asc-003 | L7 → L3(v005) | 终验完成态无 MCP 出口 + TUI 缺 completed 渲染，上升补齐 |
| asc-004 | L7 → L3(v006) | TUI 面板固定高度 Static 无法真实滚动（max_scroll_y 恒 0）+ 终验测试统计有误，上升修正 |
| asc-005 | L7 → L3(v007) | 三项结构性缺陷：回滚倒带待办、占位符可入基线、过期门控悬挂 |

## descent-4 交付内容（asc-003）

1. **se_complete_project**：终验闭环的唯一入口。前置校验（当前层 = L7-终验、L1–L6 全部 baselined、无未解决 blocking 门控），不满足时返回结构化 error 与未满足项清单；成功时 L7 README 置 completed、manifest 写 `layer_states[L7].status=completed` 与 `completed_at`，并追加 changelog。
2. **TUI completed 渲染**：层状态图新增 🏁 bold green 分支，终验完成后可正确显示完成态。
3. **部署一致性修复**：此前 TUI 修复只改了源码、未重新安装到 `.venv` 与 MCP 插件，导致「已有修复但界面仍旧」的假象；本轮完成重装并复验。

## descent-5 交付内容（asc-004）

**TUI 面板结构性重做**（这是"有数字、没滚动条、内容不全"的真正根因）：

- 旧实现：固定高度 `Static` 直接渲染 rich `Panel`。Textual 把 rich renderable 转成按视口裁剪的 `Visual`，`virtual_size` 恒等于容器高度，`overflow-y` 因此永远没有可滚动内容
- 新实现：`VerticalScroll` 容器（40/35/25%）包裹 `height: auto` 的内层 `Static#*-content`
- 待办表格重做：`expand=True`、Layer 列 min/max + fold、状态独立列（✅/⏳/🔒/🔓）、内容列 `ratio=1`、标题改为「N/M 已完成, K 待确认」——修复列宽截断导致的"内容显示不对"
- 契约测试：`test_todo_panel_is_actually_scrollable` 断言 `max_scroll_y > 0` 且滚动后 `scroll_y > 0`

实测（110x32）：top/mid/bottom `max_scroll_y` = 18/39/49，三个面板滚动条常驻。

## descent-6 交付内容（asc-005）

三项结构性修复（L3 v0.6 设计落实）：

1. **待办生命周期契约**：`rollback_to_baseline` 恢复基线正文后回填**现场待办段**与 `todo_descent`——回滚是回退设计产物，不再倒带工作进度。此前 asc-002~004 每轮回滚都把 L3 待办覆盖回模板占位符，导致面板显示「L3 ⏳ 初始化本层工作」
2. **基线占位符守卫**：`se_baseline(force=False)` 在待办仍为 `- [ ] 初始化本层工作` 时拒绝并给出 hint；`se_complete_project` 前置条件追加占位符检查。占位符不再可能被冻结进基线
3. **门控清理**：新增 `se_purge_confirmations(before_descent=0, resolution="superseded")`；`se_complete_project` 完成前自动结转较早轮次的非阻塞门控并回报 `purged_confirmations`，blocking 门控仍阻断。此前 descent-2 的非阻塞门控在项目完成后仍永久悬挂

## 流程违规与补救披露（延续）

descent-2 终验后的三次热修（chg-032/033/034）已由 asc-002 补救并立规 DESC-001（基线后缺陷必须 ascend）。descent-4 本身即是按 DESC-001 执行的第四次下降：发现完成态缺口后先上升、改设计（L3 v0.4/v005）、再下降实现，未走热修。

## 功能实现清单（终态）

### 存储层
- [x] Project 初始化（7 层目录树 + manifest + changelog + ascensions）
- [x] 基线冻结/回滚、文档 CRUD、Todo 跨层扫描、原子变更日志
- [x] 状态目录 `.vinw/`
- [x] todo_descent 写入轮次追踪

### 工作流引擎
- [x] 基线化、上升回溯、下降推进、阻塞门控、下降可行性检查
- [x] **完成态迁移（se_complete_project）**
- [x] 实际经历 3 次上升 + 4 次下降全流程验证

### MCP Tools（18 个 + 自举）
- [x] 全量工具（见 api-design.md v0.4 工具清单）
- [x] se_init_project 接管模式（adopted=true）
- [x] se_check_consistency 代码定位（manifest.code_root + code_scope 混合）
- [x] **se_complete_project**（完成态迁移，v0.4 新增）

### TUI
- [x] 3 面板布局、2 秒自动刷新、面板常驻滚动条（overflow-y: scroll）
- [x] 刷新容错（瞬时文件错误保留上次渲染）
- [x] completed 状态渲染（🏁）
- [x] 无头渲染测试覆盖（test_tui.py 4 例）

## 测试覆盖（终态）

| 模块 | 用例数 | 结果 |
|------|--------|------|
| test_project.py（含 todo 追踪 3 例） | 13 | 13/13 ✅ |
| test_state_machine.py | 11 | 11/11 ✅ |
| test_consistency_llm.py | 10 | 10/10 ✅ |
| test_search.py | 7 | 7/7 ✅ |
| test_bootstrap.py（含完成态 3 例） | 10 | 10/10 ✅ |
| test_tui.py（含真实滚动断言） | 5 | 5/5 ✅ |
| test_todo_lifecycle.py（新增） | 15 | 15/15 ✅ |
| **合计** | **71** | **71/71 ✅** |

端到端实测：MCP 自举加载 ✅；一致性检查 20/20 ✅；se_complete_project 前置校验与成功路径 ✅；TUI 渲染/滚动/容错/completed ✅。

## 已知限制

1. **LLM 审计需外部调用**：`method='llm'` 仅构造 prompt，实际 LLM 调用由 agent harness 执行。
2. **TF-IDF 需 scikit-learn**：未安装时自动降级到 ripgrep。
3. **TUI 未做交互式端到端测试**：无头渲染已覆盖，真机交互未系统测试。
4. **单活动工程**：`_active_project` 为进程内单例，多工程映射待后续版本。
5. **DESC-001 靠决议约束而非引擎强制**：状态机未在基线后拦截直接文件修改，后续可加校验层。

## 结论

**六次下降、五次上升全部闭环，71 个单元测试全部通过，完成态迁移能力补齐，自举与跨 harness 能力端到端验证成功。VINW 项目达到可交付状态。**
