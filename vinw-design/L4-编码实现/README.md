---
baseline_version: v017
baselined_at: '2026-11-14T10:47:51.907317+00:00'
descent_count: 1
doc_type: layer-readme
layer: L4-编码实现
se_version: '2.0'
started_at: '2026-11-13T10:15:00Z'
status: baselined
todo_descent: 18
---

# L4-编码实现

## 当前待办

- [x] 路径解析登记（幂等）
- [x] _invalidate_above + current 层保护
- [x] 完成戳清理
- [x] se_get_project 单次 detect_drift
- [x] TUI 三栏重构与澄清就地裁决
- [x] reviewer19 17 项处置

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