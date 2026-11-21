---
se_version: "2.0"
layer: "L7-终验"
doc_type: "final-report"
status: "in_progress"
---

# 终验报告 — VINW（descent-21/22，接管现有代码仓 v0.23）

## 项目信息

| 字段 | 值 |
|------|-----|
| 轮次 | descent-21 ~ descent-22（asc-020 需求 → asc-021 设计措辞对齐） |
| 特性 | 接管现有代码仓（adopt-existing-codebase，R36-R40） |
| 触发 | 用户场景：在已有代码仓上新增扩展/特性/bugfix 时初始化 VINW 并按螺旋工作 |

## 交付内容

| 需求 | 交付 | 验证 |
|------|------|------|
| R36 adopt 模式 | `Project.adopt()`（守卫：不存在/非目录/半初始化/非空层目录冲突；空层目录复用）+ `AdoptError.conflicts`；`se_init_project(adopt_existing=)`；CLI `--adopt-existing`；manifest `work_mode/code_root/adopted_at`；changelog `adopt` 条目 | 守卫四例 + 成功路径测试；兼容红线（默认路径逐字节不变）测试 |
| R37 变更模式引导 | `se_get_next_steps` 识别 work_mode：L1 摸底清单、L4 就地修改、special 四步（全层生效，asc-021 写明） | L1/L4/绿地三例测试 |
| R38 L1 待办种子 | `ADOPT_TODO_SECTION` 摸底五节替换占位符 | 种子内容测试 |
| R39 文档 | README "Adopting an existing repository" 章节 + 安装 prompt 步骤 3 adopt 分支 | 章节存在且与实现一致 |
| R40 摸底与初始锚定 | 设计契约：《现状摸底》六节结构、text 修正循环（复用 TextConsistencyChecker）、首次基线 ensure() 锚定、存量处置复用 triage `accept_as_is`/`defer`、债务清单进 proposals「legacy-debt」节 | design-doc v0.23 R40 节；next_steps 引导含四步 |

## 质量证据

- 测试：372/372 PASS（新增 `tests/test_adopt_existing.py` 18 例）
- 独立评审：report-b7c9e084-01（reviewer subagent，overall=warning）9 项发现全部处置——INC-001/004（impl_bug/high）自动修正；GAP-001..004 补测试；INC-002/003/005 用户裁定 fix_design 并于 asc-021 措辞对齐
- 一致性：report-9710146e-01 passed（锚定匹配）；text 检查 0 不一致（59 文件 842 符号）
- 工具数：40 不变（契约测试通过）

## 流程记录（本轮特别之处）

1. **严格路径正规化欠账**：descent-20 遗留 design_lag（scripts/readme_stats.py）——用户裁决零特例，L1 阶段最小补 design-doc 覆盖条款 + 自审 → 漂移消除；悬挂门控 cfm-006 一并结转关闭
2. **R40 由用户当场补充**：非空仓接管必须"LLM 摸底 → 初始一致性检查 → 修正 → 基线锚定"，已入 L1 proposals R40 与 L3 契约
3. **机制查明**：design_lag 在每次"通过的检查"处重锚才消除——独立评审 + 存储报告即重锚路径
4. **两次上升**：asc-020（特性）+ asc-021（设计措辞对齐，INC-002/003/005 用户裁定 fix_design）

## 已知限制（继承）

- LLM 审计需外部调用（method=llm 仅构造 prompt）；TF-IDF 需 scikit-learn；TUI 无真机交互测试
- R40 债务清单可见性 v1 为 proposals 节（人读/agent 读），未进 se_get_project 结构化输出——实践不足再升需求

## 结论

**R36-R40 全部交付，372 测试通过，reviewer 9 项发现闭环，design-doc/api-design/implementation/test-results/README 五处文档同步。VINW 现已支持在现有代码仓上初始化并以螺旋工作流开展 feature/extension/bugfix。**
