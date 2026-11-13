---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "implementation"
updated_at: "2026-11-13T10:02:19.675591"
---

# 实现笔记

## 关键代码决策

## 与设计文档的映射

| 设计文档段落 | 代码位置 | 实现状态 |
|-------------|---------|---------|
| — | — | — |

## 待解决问题

- [ ] —

## descent-2 实现记录（asc-001，2026-11-13）

### 变更内容
1. **自举加载**（server.py）：模块导入时 `_try_load_bootstrap_project()` 探测 `cwd/vinw-design/.vinw/manifest.md` → `cwd/.vinw/manifest.md`；`se_init_project` 对已初始化目录返回 `adopted=true`
2. **一致性检查代码定位**（consistency_llm.py）：`_resolve_code_root()` 读取 manifest `code_root`；`_collect_code_files()` 支持文件/目录混合，排除 `.venv`/`build`/`node_modules`/`__pycache__`/`.git`
3. **.vinw 更名**（全仓）：`Project.se_dir` → `Project.vinw_dir`，路径字面量 `.se` → `.vinw`，vinw-design 状态目录已移动

### 验证
- `se_check_consistency`(text, scope=vinw/)：20/20 符号匹配，overall=passed → report-c88f12f4.md
- `pytest tests/`：45/45 通过（新增 test_bootstrap.py 8 例 + 一致性定位 2 例）
- MCP 自举实测：重启后自动加载 vinw-self-design（当前层 L3→下降链已推进）

## descent-3 实现记录（asc-002，2026-11-13）

将 descent-2 终验后的三项热修正式纳入 L4 基线（变更日志 chg-032/033/034）：

1. **TUI 渲染崩溃修复**（tui/app.py）：Columns + Text 非法相加 → rich Group 组合（chg-032）
2. **待办轮次追踪**（server.py + store/project.py）：se_update_todo 写入 todo_descent frontmatter；get_todos 优先读取写入轮次（chg-033）
3. **TUI 可滚动 + 刷新容错**（tui/app.py）：面板 overflow-y: scroll 常驻滚动条；refresh_ui 异常兜底保留上次渲染（chg-034）

验证：52/52 测试通过（新增 test_tui.py 4 例 + todo 追踪 3 例）
