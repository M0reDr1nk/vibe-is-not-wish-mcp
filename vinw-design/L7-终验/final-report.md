---
se_version: "2.0"
layer: "L7-终验"
doc_type: "final-report"
status: "completed"
---

# 终验报告 — VINW（descent-3，含流程补救记录）

## 项目信息

| 字段 | 值 |
|------|-----|
| 项目名称 | vinw-self-design |
| 下降轮次 | descent-1 / descent-2 / descent-3（经 asc-001、asc-002 两次上升） |
| 终验时间 | 2026-11-13 |
| 版本 | 0.2.0 |

## 各层完成状态

| 层 | 状态 | 基线 | 下降次数 |
|---|------|------|---------|
| L1-需求拆解 | ✅ baselined | v001 | 1 |
| L2-参考文献与方案搜证汇总 | ✅ baselined | v001 | 1 |
| L3-方案细化 | ✅ baselined | v001, v002, v003, **v004** | 3 |
| L4-编码实现 | ✅ baselined | v001, v002, **v003** | 3 |
| L5-测试验证 | ✅ baselined | v001, v002, **v003** | 3 |
| L6-检视清理 | ✅ baselined | v001, v002, **v003** | 3 |
| L7-终验 | ✅ completed | — | 3 |

## 上升记录（ascensions.md）

| ID | 路径 | 原因 |
|----|------|------|
| asc-001 | L7-终验 → L3-方案细化(v002) | 新增自举能力，需更新 L3 接口设计 |
| asc-002 | L7-终验 → L3-方案细化(v003) | descent-2 终验后三项热修未走流程，补救上升 |

## 流程违规与补救披露（诚实性记录）

descent-2 终验完成后，曾以热修方式直接修改已基线代码三次（chg-032 TUI 渲染崩溃、chg-033 待办轮次失真、chg-034 TUI 滚动容错），未触发上升、未重新基线，导致当版终验报告失真。经审查发现后：

1. **asc-002 正式上升**，descent-3 将三项热修全部纳入 L4 基线 v003 与测试证据
2. **决议 DESC-001** 写入 `.vinw/decisions.md`：基线后缺陷一律 ascend，禁止热修（崩溃类例外，须 24h 内补流程）
3. 本报告为重写版本，替代失真版本

## 功能实现清单

### 存储层
- [x] Project 初始化（7 层目录树 + manifest + changelog + ascensions）
- [x] 基线冻结/回滚、文档 CRUD、Todo 跨层扫描、原子变更日志
- [x] 状态目录 `.vinw/`

### 工作流引擎
- [x] 基线化、上升回溯、下降推进、阻塞门控、下降可行性检查
- [x] **实际经历 2 次上升 + 3 次下降全流程验证（含补救轮）**

### MCP Tools（17 个 + 自举）
- [x] 全量工具（见 api-design.md v0.3 工具清单）
- [x] se_init_project 接管模式（adopted=true）
- [x] se_check_consistency 代码定位（manifest.code_root + code_scope 混合）
- [x] se_update_todo 写入轮次追踪（todo_descent）

### TUI
- [x] 3 面板布局、2 秒自动刷新、面板可滚动（常驻滚动条）
- [x] 刷新容错（瞬时文件错误保留上次渲染）
- [x] 无头渲染测试覆盖（test_tui.py 4 例）

## 测试覆盖（终态）

| 模块 | 用例数 | 结果 |
|------|--------|------|
| test_project.py（含 todo 追踪 3 例） | 13 | 13/13 ✅ |
| test_state_machine.py | 13 | 13/13 ✅ |
| test_consistency_llm.py | 10 | 10/10 ✅ |
| test_search.py | 7 | 7/7 ✅ |
| test_bootstrap.py | 8 | 8/8 ✅ |
| test_tui.py（新增） | 4 | 4/4 ✅ |
| **合计** | **52** | **52/52 ✅** |

端到端实测：MCP 自举加载 ✅；一致性检查 20/20（report-c88f12f4、report-8d739430）✅；TUI 渲染/滚动/容错 ✅。

## 已知限制

1. **LLM 审计需外部调用**：`method='llm'` 仅构造 prompt，实际 LLM 调用由 agent harness 执行。
2. **TF-IDF 需 scikit-learn**：未安装时自动降级到 ripgrep。
3. **TUI 未做交互式端到端测试**：无头渲染已覆盖，真机交互未系统测试。
4. **单活动工程**：`_active_project` 为进程内单例，多工程映射待后续版本。
5. **热修流程约束靠决议而非引擎强制**：DESC-001 目前靠遵守，状态机未在 `se_baseline` 后拦截直接文件修改（后续可考虑校验层）。

## 结论

**三次下降、两次上升全部闭环，52 个单元测试全部通过，自举能力端到端验证成功，流程违规已补救并立规。VINW 项目达到可交付状态。**
