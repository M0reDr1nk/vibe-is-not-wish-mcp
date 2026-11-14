---
created_at: '2026-11-13T10:55:25.613298+00:00'
doc_type: cleanup-log
layer: L6-检视清理
se_version: '2.0'
updated_at: '2026-11-13T10:55:25.613298+00:00'
---

---
se_version: "2.0"
layer: "L6-检视清理"
doc_type: "cleanup-log"
status: "completed"
---

# 检视清理记录

## 代码风格检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| PEP8 合规 | 通过 | 无格式问题 |
| 类型注解 | 通过 | 核心函数均有类型注解 |
| 导入清理 | 已修复 | 移除未使用的 ConsistencyChecker 导入 |

## Bug 修复

| 问题 | 严重性 | 修复 |
|------|--------|------|
| server.py 缺少 frontmatter 导入 | 🔴 高 | 已添加 `import frontmatter` |
| consistency_llm.py 残留 utcnow() | 🟡 中 | 已替换为 datetime.now(timezone.utc) |

## 废弃代码清理

| 文件 | 操作 | 原因 |
|------|------|------|
| `vinw/workflow/consistency.py` | 删除 | 已被 consistency_llm.py 替代 |

## 依赖对齐

| 变更 | 说明 |
|------|------|
| pyproject.toml dev +scikit-learn | TF-IDF 搜索需要 |

## 文档更新

| 文件 | 变更 |
|------|------|
| README.md | 添加 se_store_consistency_report、se_search_proposals 工具说明 |
| vinw/__init__.py | 添加 __version__ = "0.2.0" |

## 测试复验

- 36/36 单元测试通过 ✅
- 一致性检查：20 条 WARNING 全部为已知误报（设计项目与代码项目分离导致）
## descent-2 清理（asc-001，2026-11-13）

| 类别 | 操作 | 说明 |
|------|------|------|
| 废弃产物 | 删除 `build/` 并加入 .gitignore | pip 构建残留，setuptools 每次重装会再生成 |
| 缓存清理 | 删除全部 `__pycache__/`（已在 .gitignore） | 5 个目录 |
| 仓库卫生 | `git rm --cached .DS_Store` | 停止跟踪系统垃圾文件 |
| 调试代码 | 全量扫描 pdb/breakpoint/TODO/FIXME | 零命中（validators.py 的 "vXXX" 为正常错误提示文案） |
| 文档同步 | README / kimi.plugin.json / SKILL.md / design-doc / populate_design.py | `.se` → `.vinw` 引用统一（38 处） |
| 状态目录 | `vinw-design/.se` → `vinw-design/.vinw` | 与 L3 v0.3 设计一致 |

测试复验：45/45 通过 ✅

## descent-3 清理（asc-002 流程补救，2026-11-13）

| 类别 | 操作 | 说明 |
|------|------|------|
| 流程清理 | 热修 chg-032/033/034 纳入正式基线 | 消除"基线后修改"的游离状态 |
| 决策记录 | DESC-001 写入 .vinw/decisions.md | 基线后缺陷必须走上升，禁止热修（崩溃类除外且 24h 内补流程） |
| 测试复验 | 52/52 通过 ✅ | 含 TUI 无头渲染 4 例 |

## descent-4 清理（asc-003 完成态迁移，2026-11-13）

| 类别 | 操作 | 说明 |
|------|------|------|
| 能力补齐 | se_complete_project 暴露为 MCP 工具 | 消除 mark_layer_completed 无出口的缺口 |
| TUI 渲染 | completed 状态分支（🏁 bold green） | 终验完成后层图可正确显示完成态 |
| 部署一致性 | .venv 重装 + MCP 插件重装 | 修复"改了代码但运行时未生效"导致的滚动条假象 |
| 测试复验 | 55/55 通过 ✅ | 新增完成态迁移 3 例 |

## descent-5 清理（asc-004 TUI 布局契约，2026-11-13）

| 类别 | 操作 | 说明 |
|------|------|------|
| 未使用导入 | 移除 `Horizontal`, `Vertical` | compose 改用 VerticalScroll 后不再使用 |
| 渲染裁剪 | 固定高度 Static → VerticalScroll + auto 内容 | 消除「有数字无滚动条」的结构性缺陷 |
| 文档纠错 | L7 终验报告测试统计由 58 修正为真实值 | 逐文件重新统计（bootstrap 10、state_machine 11） |
| 测试复验 | 56/56 通过 ✅ | 含真实滚动断言 |

## descent-6 清理（asc-005 结构修复，2026-11-13）

| 类别 | 操作 | 说明 |
|------|------|------|
| 待办数据 | L3 README 补齐真实待办并重冻结为 v008 | asc-005 回滚到 v006（旧代码，未含待办保留逻辑）导致占位符复现 |
| 历史快照瑕疵 | 记录 L3 v007 快照内含模板占位符 | v008 重冻结修正；新契约下回滚不再倒带待办，不会复现 |
| 测试适配 | test_state_machine 机制类用例改 force=True | 基线守卫生效后的预期行为变更 |
| 未使用导入 | 检查 vinw/ 全量 | 无残留（descent-5 已清理 Horizontal/Vertical） |
| 测试复验 | 71/71 通过 ✅ | 含 15 例新增结构修复覆盖 |

## descent-7 清理（asc-006 多项目跟踪管理，2026-11-13）

| 类别 | 操作 | 说明 |
|------|------|------|
| 未使用导入 | 移除 10 处（__main__/tui.app/consistency_llm/search/document/project） | 静态 AST 扫描发现，含历史遗留 shutil/yaml/json/subprocess/Counter/frontmatter |
| 构建产物 | 删除 build/、__pycache__/、临时 VINW_HOME | 保持工作区干净 |
| 文档同步 | api-design v0.7 / code-map / implementation / test-results / iterations | 多项目能力全覆盖 |
| 注册表实登 | `se_register_project` 登记 vinw-self-design | 供 TUI 选择器与多项目工具实测 |
| 测试复验 | 101/101 通过 ✅ | 清理后重跑全绿 |

## descent-8 清理（asc-007 注册表改 SQLite，2026-11-14）

| 类别 | 操作 | 说明 |
|------|------|------|
| 未使用导入 | AST 全量扫描 | 结果：0 处（descent-7 清理后保持干净） |
| gitignore | 追加 `*.db` / `*.db-wal` / `*.db-shm` / `*.db.corrupt-*` | 注册表默认在 `$VINW_HOME`（仓外）；防止 VINW_HOME 指向仓内时误提交 SQLite 文件与 WAL 附属文件 |
| 遗留数据 | `~/.vinw/registry.json` → `.migrated-*` 保留 | 迁移后原文件不删除，符合"不静默删数据"约束 |
| 文档同步 | api-design v0.8 / code-map / implementation / test-results / iterations / synthesis 更正声明 | 全链路已更新 |
| 测试复验 | 112/112 通过 ✅ | 清理后重跑全绿 |

## descent-9 清理（asc-008 一致性门控，2026-11-14）

| 类别 | 操作 | 说明 |
|------|------|------|
| 死代码删除 | 删除 `vinw/workflow/gate.py`（GateManager 80 行） | 全仓无引用：早期"把确认块嵌入文档"的方案已被 manifest 驱动的门控取代；保留会误导后续维护 |
| 未使用导入 | consistency_gate.py 移除 re/datetime/timezone/Path/_display_path；consistency_llm.py 移除 json | AST 扫描发现（json 用于构建指纹 metadata 后被 frontmatter.dumps 取代） |
| 一致性报告 | 本轮新增 report-f6edf36a（含 descent=9 + 指纹） | 历史报告无指纹，`latest_passing(descent)` 按轮次筛选后不受影响 |
| 测试复验 | 126/126 通过 ✅ | 清理后重跑全绿 |

## descent-12 清理（asc-011 审计分级裁定，2026-11-14）

| 类别 | 操作 | 说明 |
|------|------|------|
| 未使用导入 | consistency_llm.py 移除 3 个已不用的 symbols 导入 | 行号提取接手后 extract_code_symbols/filter_symbols/extract_design_identifiers 不再直接调用 |
| 报告可读性 | 把 inconsistencies 写入 frontmatter | 裁定需要机器可读的 findings，此前只有 gaps 入库 |
| 旧报告兼容 | 历史报告无 kind/descent 时按 text 处理 | `latest_passing(kind=...)` 使用 `meta.get("kind") or "text"` |
| 设计同步 | api-design v0.13 补 required/advisory 规则与 .tsx/.js 默认扩展名 | 对应裁定 INC-005 / INC-007（用户批准 fix_design） |
| 测试复验 | 184/184 通过 ✅ | 清理后重跑全绿 |

## descent-14 清理（asc-013 全阶段审计契约，2026-11-14）

| 类别 | 操作 | 说明 |
|------|------|------|
| 未使用导入 | AST 全量扫描 | 0 处 |
| 陈旧断言 | 将退化为 `pytest.raises(Exception)` 的用例收紧为精确异常 | 该退化为 reviewer9 指出，曾掩盖顺序缺陷 |
| 文档纠偏 | 流程图补第二次 ensure、strict 作用域、config_error 双重语义、测试数快照 | 对应 reviewer11 的 4 项文档发现 |
| 构建产物 | 清理 `build/`、`__pycache__` | — |
| 测试复验 | 275/275 通过 ✅ | — |

## descent-15 清理（backlog 3）

| 项 | 说明 |
|----|------|
| 测试污染 | 新增 `tests/conftest.py`，autouse 隔离 `VINW_HOME` 并重置注册表单例 |
| 真实数据修复 | `ProjectRegistry.prune()` 清除 23 条 `/pytest-of-*` 幽灵条目，现存 1 条（vinw-self-design） |
| 异常边界 | `_register_quietly` 由 `except Exception` 收窄为 `(OSError, sqlite3.Error, ValueError)`，并 `logging.warning(exc_info=True)` 留痕 |
| 文档一致性 | 方案编号统一（扫描发现=B）、README 故障排查行更新、设计补 name/warning/异常边界/测试隔离 |
| 测试复验 | 287/287 通过 ✅ |

### descent-15 追加（reviewer13 复核）

| 项 | 说明 |
|----|------|
| touch 容错 | `se_use_project` 的 `touch()` 移入 `(OSError, sqlite3.Error)` 容错范围，登记先行 |
| 文档索引 | 版本历史补 v0.15/v0.16 行；checkpoints.md 工具数 18→36 |
| 测试复验 | 287/287 通过 ✅ |

## descent-16 清理（R31 + R30）

| 项 | 说明 |
|----|------|
| 未使用导入 | AST 全量扫描：0 处 |
| 调试残留 | `breakpoint()` / `pdb` / DBG 打印：0 处 |
| 测试 hack | **清理被门控拦下并已回退**：改测试等于改代码，在 L6（设计已冻结）会触发 design_lag。两处 hack（`if False` 死代码、函数内重复 import）无害，留待下一轮 L4 随代码改动一并清理 |
| 工具清单 | `scripts/gen_tool_catalog.py` 重新生成（38 个工具，含 2 个新澄清工具） |
| 文档同步 | v0.17 设计（reviewer14 定稿版）、README 3.5 重启规则、R33 backlog 登记 |
| 进程卫生 | 安装后重启 MCP server（R30 教训实践） |
| 测试复验 | 303/303 通过 ✅ |

## descent-17 清理（v0.18 harness）

| 项 | 说明 |
|----|------|
| changelog 解析 | 移除文本解析（会双计且不可机读），改读 manifest 结构化记录 |
| markdown 表格 | assumption-taken 的 reason 用中文分号分隔，避免 `|` 破坏表格 |
| 死代码 | `_assumption_entries` 重写，移除 `assumptions[-20:]` 静默截断 |
| README | 工具数 38 → 39，补 3 个澄清工具 |
| 测试 hack | 无 |
| 测试复验 | 316/316 ✅ |

## descent-18 清理（v0.19）

| 项 | 说明 |
|----|------|
| `_refresh_ui` 死代码 | 删除旧的 recent/hints/todos 读取（每 2s 无谓 I/O） |
| 重复登记 | `se_use_project` 中第二次 `_register_quietly` 删除 |
| 重复计算 | `se_get_project` 的 `detect_drift` 由 2 次降为 1 次 |
| 重复文案 | 问题块不再重复 drift_lines 的处置/变更文件 |
| 死键 | `_CHANGE_STYLE.force-baseline` 删除，补 `purge-confirmations` |
| 测试复验 | 333/333 ✅ |
