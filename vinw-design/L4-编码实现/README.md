---
baseline_version: v016
baselined_at: '2026-11-14T09:45:40.818787+00:00'
descent_count: 1
doc_type: layer-readme
layer: L4-编码实现
se_version: '2.0'
started_at: '2026-11-13T10:15:00Z'
status: baselined
todo_descent: 17
---

# L4-编码实现

## 当前待办

- [x] 实现 impact/reversibility 与自动阻塞推导
- [x] 实现 assumption-taken 留痕（含 deviation）
- [x] 实现 se_clarification_brief（读 manifest）
- [x] 引擎层阻塞澄清守卫（baseline/descend）
- [x] 转换返回体注入 pending_clarifications
- [x] reviewer18 11 项发现处置

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