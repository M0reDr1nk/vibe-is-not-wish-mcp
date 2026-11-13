---
se_version: "2.0"
layer: "L5-测试验证"
doc_type: "test-plan"
status: "completed"
updated_at: "2026-11-13T12:00:00Z"
---

# 测试计划

## 测试范围

本轮测试覆盖 descent-1 中实现的核心模块：

1. **存储层** (`vinw/store/project.py`) — Project 初始化、基线冻结/回滚、文档 CRUD、todo 扫描
2. **工作流引擎** (`vinw/workflow/state_machine.py`) — baseline、ascend、descend、确认门控
3. **一致性检查** (`vinw/workflow/consistency_llm.py`) — LLM 审计 prompt 构造、text fallback 符号提取与匹配
4. **方案搜索** (`vinw/workflow/search.py`) — ripgrep 文本搜索、TF-IDF 向量搜索
5. **MCP Server** (`vinw/server.py`) — tools 注册完整性
6. **TUI** (`vinw/tui/app.py`) — 启动与初始化

## 测试策略

| 模块 | 方法 | 覆盖率目标 |
|------|------|-----------|
| project.py | pytest 单元测试 | 核心路径 100% |
| state_machine.py | pytest 单元测试 | 核心路径 100% |
| consistency_llm.py | pytest 单元测试 | 核心路径 100% |
| search.py | pytest 单元测试 | 核心路径 100% |
| server.py | 导入验证 + tools 清单核对 | 注册完整性 |
| tui/app.py | 导入 + 实例化验证 | 启动可用性 |

## 测试环境

- Python 3.12
- pytest 9.2.0
- dependencies: python-frontmatter, pyyaml, scikit-learn (TF-IDF 可选)

## 已知限制

- TF-IDF 搜索需 scikit-learn，未安装时自动降级到 ripgrep
- LLM 审计模式需外部 LLM 调用，本轮仅验证 prompt 构造逻辑
- TUI 仅验证启动，未做交互式端到端测试
