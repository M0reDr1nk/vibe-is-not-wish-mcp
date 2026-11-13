---
se_version: "2.0"
layer: "L7-终验"
doc_type: "final-report"
status: "completed"
---

# 终验报告 — VINW（含 descent-2 自举轮）

## 项目信息

| 字段 | 值 |
|------|-----|
| 项目名称 | vinw-self-design |
| 下降轮次 | descent-1 + descent-2（经 asc-001 上升） |
| 终验时间 | 2026-11-13 |
| 版本 | 0.2.0 |

## 各层完成状态

| 层 | 状态 | 基线 | 下降次数 |
|---|------|------|---------|
| L1-需求拆解 | ✅ baselined | v001 | 1 |
| L2-参考文献与方案搜证汇总 | ✅ baselined | v001 | 1 |
| L3-方案细化 | ✅ baselined | v001, v002, **v003** | 2 |
| L4-编码实现 | ✅ baselined | v001, **v002** | 2 |
| L5-测试验证 | ✅ baselined | v001, **v002** | 2 |
| L6-检视清理 | ✅ baselined | v001, **v002** | 2 |
| L7-终验 | ✅ completed | — | 2 |

## descent-2 变更摘要（asc-001：L7 → L3 v002）

1. **自举加载**（server.py）：启动自动探测 `cwd/vinw-design/.vinw/manifest.md` → `cwd/.vinw/manifest.md` 并加载为活动工程；`se_init_project` 支持接管已有工程（`adopted=true`）。VINW 可在自身代码仓中管理自身设计工程。
2. **一致性检查代码定位规则**：manifest 新增 `code_root`；`code_scope` 支持文件/目录混合；排除 `.venv`/`build` 等目录。修复了自举场景 20 符号误报缺陷（INC，已全部消除）。
3. **状态目录更名**：`.se/` → `.vinw/`（含 `Project.se_dir` → `Project.vinw_dir`），全仓 38 处引用统一适配。

## 门控记录

| 门控 | 层 | 决议 |
|------|-----|------|
| cfm-20261113-153121-001 | L3 | **modify**（批准 + .vinw 更名反馈，已执行） |
| cfm-20261113-154455-002 | L5 | 非阻塞，待用户 review |

## 功能实现清单

### 存储层

- [x] Project 初始化（7 层目录树 + manifest + changelog + ascensions）
- [x] 基线冻结/回滚（freeze_baseline / rollback_to_baseline）
- [x] 文档 CRUD（read_document / write_document）
- [x] Todo 跨层扫描（get_todos）
- [x] 原子变更日志（append_changelog_entry）
- [x] **状态目录 `.vinw/`（descent-2）**

### 工作流引擎

- [x] 基线化（baseline）
- [x] 上升回溯（ascend）— 创建新 descent 轮次，标记下层 superseded
- [x] 下降推进（descend）— 校验中间层已 baselined
- [x] 阻塞门控（require_confirmation / resolve_confirmation）
- [x] 下降可行性检查（can_descend_to_next）

### MCP Tools（17 个 + 自举）

- [x] se_init_project（**+ adopt 接管模式**）, se_get_project
- [x] se_baseline, se_list_baselines
- [x] se_ascend, se_descend, se_can_descend
- [x] se_require_confirmation, se_resolve_confirmation
- [x] se_store_document, se_read_document, se_list_documents
- [x] se_log_change, se_get_changelog
- [x] se_check_consistency（method: llm / text / ast；**+ code_root 定位**）
- [x] se_store_consistency_report
- [x] se_search_proposals（method: rg / tfidf）
- [x] se_get_todos, se_update_todo
- [x] se_get_next_steps

### TUI

- [x] SEApp 导入与实例化
- [x] 3 面板布局（层状态图 + todo/待确认 + 状态与变更）

## 测试覆盖（descent-2）

| 模块 | 用例数 | 结果 |
|------|--------|------|
| test_project.py | 10 | 10/10 ✅ |
| test_state_machine.py | 13 | 13/13 ✅ |
| test_consistency_llm.py | 10 | 10/10 ✅ |
| test_search.py | 7 | 7/7 ✅ |
| test_bootstrap.py（新增） | 8 | 8/8 ✅ |
| **合计** | **45** | **45/45 ✅** |

端到端实测：MCP 自举加载 vinw-self-design ✅；一致性检查 20/20 匹配（report-c88f12f4）✅；上升/下降/门控/基线全链路实操 ✅。

## 已知限制

1. **LLM 审计需外部调用**：`method='llm'` 仅构造 prompt，实际 LLM 调用由 agent harness 执行。
2. **TF-IDF 需 scikit-learn**：未安装时自动降级到 ripgrep。
3. **TUI 未做交互式端到端测试**：仅验证启动与实例化。
4. **单活动工程**：`_active_project` 为进程内单例，多工程映射待后续版本。

## 结论

**descent-2 全部 7 层完成，45 个单元测试全部通过，自举能力端到端验证成功。VINW 已能在自身代码仓中自举运行，项目达到可交付状态。**
