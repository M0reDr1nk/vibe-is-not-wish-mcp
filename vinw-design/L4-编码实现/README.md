---
baseline_version: v020
baselined_at: '2026-11-21T14:19:33.316645+00:00'
descent_count: 1
doc_type: layer-readme
layer: L4-编码实现
se_version: '2.0'
started_at: '2026-11-13T10:15:00Z'
status: baselined
todo_descent: 21
---

# L4-编码实现

## 当前待办

- [x] L4 v0.23 实现：Project.adopt + AdoptError + 脚手架共享 + se_init_project(adopt_existing) + CLI --adopt-existing + next_steps 引导
- [x] tests/test_adopt_existing.py 12 例；全量 366/366 通过；README Adopting 章节 + 安装 prompt
- [ ] L4 基线：一致性门控（text 重查 + LLM 审计 + 裁定）→ 下降 L5

- [x] extra 写入 + 转义 + 行分隔符归一
- [x] 行级状态机解析器（围栏优先）
- [x] alignment 9 字段 + 布尔类型化
- [x] se_get_changelog / TUI 共享解析器
- [x] r23 8 项发现全部处置

## 阶段小结

（阶段完成时填写）

## 基线记录

| 版本 | 冻结时间 | 原因 |
|------|---------|------|
| — | — | — |

## 实现笔记

### se_check_consistency (LLM + text)

- `LLMConsistencyAuditor.audit()`: 构建结构化 prompt，将 design-doc + code 全文传给 LLM 做语义比对
- `LLMConsistencyAuditor.store_report()`: 将 LLM 返回的 JSON 解析并写入 `consistency-reports/report-{id}.md`
- `TextConsistencyChecker.check()`: 本地文本匹配，提取 design 中的函数名并在代码中搜索存在性
- `method` 参数: `"llm"` (默认) / `"text"` (fallback) / `"ast"` (预留，fallback 到 llm)

### se_search_proposals (rg + TF-IDF)

- `ProposalSearcher._search_rg()`: ripgrep 风格文本搜索，关键词计数 + 归一化评分
- `ProposalSearcher._search_tfidf()`: sklearn TF-IDF + 余弦相似度，按需启用
- `scope`: `"local"` (当前项目) / `"archive"` (指定归档目录)

### 已知问题

- text 方法存在路径边界误报（设计项目与代码项目分离时）
- 表头提取仍有边缘 case（已优化但未完全消除）