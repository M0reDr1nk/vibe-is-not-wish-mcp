---
auditor: reviewer
auditor_model: independent-subagent (descent-21 L4 exit audit)
checked_at: '2026-11-21T13:54:40.244298+00:00'
code_fingerprint: c4be8dbb82910a9fa7764c7579267eba99eacd6871fc108ce1951c221a0df0be
code_symbols_count: 891
descent: 21
design_hash: 5e325bce6eab585896f9893be5a38426ad1134f301087ae8665fe857e41ae7cf
design_hash_algo: layer-v1
doc_type: consistency-report
extensions:
- .py
- .c
- .h
- .cc
- .cpp
- .hpp
- .rs
- .go
- .java
- .ts
- .tsx
- .js
file_hashes:
  example/gemm/bench/bench_gemm.c: e1c80082608700e77f522c5948cee26aaff4644987c451e9bb6c5af5c1f15fe8
  example/gemm/include/gemm.h: f342928198f5d6a080a1971cdd116296518faef29746778c2cfc69e1cbe243f6
  example/gemm/src/amx_asm.h: 90bf64b865b4cb4421265df9d08f168789d5ae8d7cc51257d1b3ebf174881d77
  example/gemm/src/gemm_amx.c: fc7f4fd40a2c593f6e5557427e7d122d55a81e70376e9b1f7f9cf77c7b53aaac
  example/gemm/src/gemm_blocked.c: e4f403ca69cbec93ed526405bf8f1eb6a6ec51c273adbc60ab9aef24e267809b
  example/gemm/src/gemm_ref.c: e6c6bd2d4e306d8cd77a42b0c33128b4c41525437991116487ab2b2904a172b3
  example/gemm/tests/test_gemm.c: ea9f7e4f462cb83d6fc8bd22a09d08d210f8dd5ad4e7e4889adf91121a410ee6
  scripts/finalize_l3.py: 5176547944f0ff14ba9ca3d35df4ad377a1018181ad0fe9ab51ed6f7f400d8f0
  scripts/gen_tool_catalog.py: 36c8291494c97208b0e662df572f347fdb81c806b1aa30393e4b4ad51717f0dc
  scripts/l4_finalize.py: 761e29c5ad0f466aa677125edc53cfb5ec06fb30bfc2922db3a65cb202f1dfba
  scripts/l4_round1_finish.py: 1800e7da6754e74fa3abb186ecb8451fe91a0701381ecedc81d1486731ece2db
  scripts/l5_finalize.py: f7976bf02207a460bf2ae2af64103e33caca8ccc63136226f1c3fb77f0e9c848
  scripts/l6_finalize.py: 77e767e56e109208e2f0f311b1819e3452eac7e212e2e76788ebbd0887a0bb4e
  scripts/l7_finalize.py: d5910c6ea9ab18133f0db15073547423f7a081b33a24b4b58817d8973626eb1f
  scripts/populate_design.py: bd4f6a5039d322e5ae1ef1d897fd5e43873a57754e26388990dc5933d47f8390
  scripts/readme_stats.py: ea2781e8c99523718b14883b6e0423b7dc87197132326a490d6b9db9663c0cd8
  scripts/run_consistency_check.py: 0c54c40d27bb0647f2c7bbeb2e4e71a04f1ccda4509c230f0ac077c62a74de1a
  tests/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  tests/conftest.py: 55bce5036f8ee83ef6a3e5007907b923dd1df479ebf317dff0a9284e85d035f2
  tests/test_adopt_existing.py: 3605e0c21b0e56eff763b8874f991ea2d7fd31fa43b629a827dd5fa8dfdfc381
  tests/test_audit_persistence.py: 2200118e2a921bb922825245ec4b2834a7a203a018a257b5fc19246b6fd27e23
  tests/test_audit_policy.py: 2e4ad31b3406c45d57bace89331074c1ce5983d75c13c7419609f3b86577a237
  tests/test_bootstrap.py: a7f08d336350b3bf7dec432488ddcb600ca697526068ed2e20909c305a88285a
  tests/test_consistency_gate.py: b6db508d23e3f35a6c09949ccfac43f6d3ec6a3d5e11d785bdaaa0439e3dba4d
  tests/test_consistency_llm.py: 73f6dd5f505a4a16e1a86c07aa72736b11deabecdaf6c936bed551c812c86ab1
  tests/test_contract_v014.py: 4c485b60ec29ee7a7d080f173eb9d5722ec24f6513fe7e27d19504c8b0ab2dfd
  tests/test_drift.py: 55c9ba2e6f891b2e0be9d8eb0f044fffadacd206769c753ee4d4f143059b0e13
  tests/test_project.py: aa27de12f1fba588fdf451a0a43df4424f93b9e240a920138f5da5ba9b73ee55
  tests/test_registry.py: 248ac36d59cacfc16b3e76afe540738da53bfec50f3daa495a12ff2a6b6b5fbc
  tests/test_search.py: c5bea9623a6825beba2db9f3572a65d033f9363538d68db5c25d24d8bdb49cd3
  tests/test_stage_heal.py: 45520049f3a24bd93bfcf77d966c8b7955a0c3fb3b34fbe015968f61704741b5
  tests/test_state_machine.py: 5d9f2f057905050b7031e0637d05127ada742a2b07b5f597bed8ace0dfc2d2b9
  tests/test_symbols.py: a25bb037a762cb7f2e52ec8a02240d63b913657edd1e3ee777217af3573e4c13
  tests/test_todo_lifecycle.py: 17fd9c6d676dc82c7bf165521f8f9f3d8372a381636078f328f5a9d1727405ad
  tests/test_triage.py: f77c9715a30b96afc68f546d5145b6a3dec5d650d2b512db0cd710546df3eec5
  tests/test_tui.py: dd580b3d5ac66f6a3b58451ef456bffa81194b0ee18404e1a2c337dbd77ecff4
  vinw/__init__.py: e97c522d6f9a8d9df85a5adac86b7cdcd488f15e880eff5f6e2ff94f7d647287
  vinw/__main__.py: 086673c8f27fb64e594bf628ee7de1b4dc48fe484998ce96c58cd2c99cbd3948
  vinw/server.py: 43d0489c7e988fc0640c5786b975d27c868a5f6bacbea5480bd091c934ee67ae
  vinw/store/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  vinw/store/changelog.py: 683940505c76078cc815bd236635e8a5f540a2f959442a26b4808497f739103e
  vinw/store/document.py: 7c5e44c5e9978f7d26b6fcdc5774111a68f1d4c220ce467520efbebdb52d82e8
  vinw/store/project.py: b1cc7ff19383eedfd0e48fd52998dde62baaa5ba196d7a16392fd8d5f8309d3b
  vinw/store/registry.py: c4a6941ddfdb4fa00948dbc363dd0c4cae0aca885eb216ed852cd07fbd8b5262
  vinw/tui/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  vinw/tui/app.py: 6b41cecf6197cfcd197d22b934acf1f5b9a87e0fba65f3b9e26d80216e9eedfd
  vinw/tui/selector.py: d478bd39bb9e03794f9e6286a41a21148ea60444b4c3e1a7f71ca5a4e102bc3c
  vinw/tui/widgets/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  vinw/utils/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  vinw/utils/templates.py: 3be84a0c20afd0fad019576153638f92fea0f3b13ebf07b263913ec538d67d83
  vinw/utils/validators.py: 913137e19a1a159c0dae92bd222b408743d5622a7baad1ee370744af74dd54b4
  vinw/workflow/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  vinw/workflow/consistency_gate.py: a8a73a42b0a7ddd69855ca76968ef65c2416f6005c5430e9fb690cacf889d765
  vinw/workflow/consistency_llm.py: 5a28a90f737bb6406e752258c243c80e523420cf8d2ebc9ed41355cbdf2ca909
  vinw/workflow/drift.py: 4cdfabe73167d52915f028a7887054cdc4b4d2d3692645b31565a3d37ef2b2db
  vinw/workflow/search.py: 62f00d317a29a51a44874b0132e14f599053be75a7b3b695e5900c832c7ba8ca
  vinw/workflow/state_machine.py: 7a951f07e69eaf3c7292e53d90b24796cb932099423859c68c5e6b0d6ee9f6c0
  vinw/workflow/symbols.py: 381f50119c490a3a25fdaf97369ca12c4384f4c8136f60277d685fdb46f25279
  vinw/workflow/triage.py: eb25f1fd6d5b45437211bc460e819c29476a86943839696b0406375dbd1d97ba
files_scanned: 59
gaps:
- description: 幂等 adopted 路径（adopt_existing=true 且 manifest 已存在 → adopted=true 且不加
    adopted_existing）无测试防护
  design_ref: api-design.md:1365
  id: GAP-001
  missing: test
  severity: warning
- description: 守卫 'root 不是目录' 无测试（测试契约只列三例）
  design_ref: design-doc.md:266
  id: GAP-002
  missing: test
  severity: warning
- description: next_steps L4 引导分支零覆盖
  design_ref: design-doc.md:303
  id: GAP-003
  missing: test
  severity: warning
- description: CLI --adopt-existing 无测试（成功输出/守卫退出码/幂等）
  design_ref: design-doc.md:296
  id: GAP-004
  missing: test
  severity: warning
gaps_count: 4
inconsistencies:
- category: logic
  code_ref: vinw/server.py:1809
  description: 设计 L1 gate 文案加（含现状摸底确认）；实现未触碰 gate_before_leave
  design_ref: design-doc.md:302
  id: INC-001
  severity: null
  suggestion: work_mode 分支对 L1 追加 gate 后缀
- category: logic
  code_ref: vinw/server.py:1868-1872
  description: 设计 L4 work '加' Modify existing code in place；实现整体替换丢弃绿地条目；special_instruction
    全层生效偏离 '其他层不变'
  design_ref: design-doc.md:303
  id: INC-002
  severity: null
  suggestion: 追加 + special 按层收窄，或修订设计
- category: interface
  code_ref: vinw/server.py:271-272
  description: 设计守卫拒绝响应含 hint；not-found/not-a-dir 分支无 hint（设计内部不一致：守卫表只写 error）
  design_ref: api-design.md:1366
  id: INC-003
  severity: null
  suggestion: 改设计标 hint 可选，或补通用 hint
- category: logic
  code_ref: vinw/__main__.py:98-107
  description: 幂等 adopted 契约在 CLI 侧未实现：FileExistsError 裸 traceback
  design_ref: design-doc.md:267
  id: INC-004
  severity: null
  suggestion: CLI adopt 前置 manifest 检查，幂等打印退出
- category: constraint
  code_ref: vinw/store/project.py:199-201
  description: 半初始化错误文案：设计字面值 vs 实现增强版（绝对路径+manifest 缺失说明）
  design_ref: design-doc.md:268
  id: INC-005
  severity: null
  suggestion: 统一文案（倾向更新设计）
inconsistencies_count: 5
kind: llm
layer: L4-编码实现
llm_verdict: warning
overall_status: warning
policy: text+llm
report_id: b7c9e084-01
se_version: '2.0'
triage:
- analysis: 实现与设计一致，缺测试回归防护
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 补 MCP 幂等测试：manifest 已存在 + adopt_existing=true → adopted=true 且无 adopted_existing
    键
  design_ref: null
  difference: api-design.md:1365 幂等 adopted 响应契约 vs 测试文件无该路径用例
  finding_id: GAP-001
  id: GAP-001
  impact: 测试覆盖率；幂等契约回归风险
  kind: inconsistency
  recommendation: fix_impl：补 MCP 级幂等测试（adopted=true 且无 adopted_existing 键）
  severity: warning
  status: fixed
- analysis: 实现已存在，纯测试遗漏
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 补 NotADirectoryError 守卫用例（文件路径充当 root）
  design_ref: null
  difference: design-doc.md:266 守卫表含 root 非目录 → 测试契约未列
  finding_id: GAP-002
  id: GAP-002
  impact: 测试覆盖率
  kind: inconsistency
  recommendation: fix_impl：补 NotADirectoryError 用例
  severity: warning
  status: fixed
- analysis: 实现存在未验证；与 INC-002 联动
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 补 L4 层 next_steps 引导测试；INC-002 裁定改设计（维持替换+全层 special），测试断言实现现状
  design_ref: null
  difference: design-doc.md:303 L4 引导 vs 测试仅 L1 层
  finding_id: GAP-003
  id: GAP-003
  impact: 测试覆盖率
  kind: inconsistency
  recommendation: fix_impl：裁定 INC-002 后按裁定补测
  severity: warning
  status: fixed
- analysis: 设计给了字面输出契约却无测试锚定；INC-004 bug 无回归网
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: capsys 补 CLI 成功输出/守卫退出码用例（幂等用例已随 INC-004 修复添加）
  design_ref: null
  difference: design-doc.md:296 CLI 输出契约 vs 无 CLI 测试
  finding_id: GAP-004
  id: GAP-004
  impact: 测试覆盖率；CLI 契约回归
  kind: inconsistency
  recommendation: fix_impl：capsys 补 CLI 成功/守卫/幂等用例
  severity: warning
  status: fixed
- analysis: 实现漏做子条款；引导弱化但无功能错误
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: impl_bug/high 自动修正（R24）：work_mode L1 分支追加 gate 后缀（含现状摸底确认），测试断言补上
  design_ref: null
  difference: design-doc.md:302 gate 文案加摸底后缀 vs server.py 未实现
  finding_id: INC-001
  id: INC-001
  impact: next_steps 输出
  kind: inconsistency
  recommendation: fix_impl：work_mode L1 分支追加 gate 后缀 + 测试
  severity: warning
  status: fixed
- analysis: '''加'' 解读分歧；全层 special 越界；后果限提示文案'
  classification: ambiguous
  code_ref: null
  confidence: medium
  decision: fix_design
  decision_note: 用户裁定：维持实现现状（L4 work 整体替换 + special_instruction 全层生效），上升回 L3 修订设计措辞写明
  design_ref: null
  difference: 设计 'L4 work 加' + '其他层不变' vs 实现整体替换 + special 全层生效
  finding_id: INC-002
  id: INC-002
  impact: next_steps 文案
  kind: inconsistency
  recommendation: fix_impl：追加语义 + special 按层收窄；设计措辞下轮写明
  severity: warning
  status: decided
- analysis: 实现选窄解读；调用方存在性断言会失配
  classification: ambiguous
  code_ref: null
  confidence: medium
  decision: fix_design
  decision_note: 用户裁定：本轮 fix_design——api-design 响应契约 hint 标为仅冲突/半初始化场景提供
  design_ref: null
  difference: api-design hint 必填 vs not-found 分支无 hint（设计内部不一致）
  finding_id: INC-003
  id: INC-003
  impact: MCP 响应 schema 契约
  kind: inconsistency
  recommendation: fix_design：hint 标为仅冲突/半初始化场景（对齐守卫表）
  severity: warning
  status: decided
- analysis: MCP 侧已实现，CLI 调用方漏实现；违反不抛裸异常精神
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: impl_bug/high 自动修正（R24）：CLI adopt 前置 manifest 存在性检查，幂等打印退出 0；竞态 FileExistsError
    友好处理；测试 test_cli_adopt_idempotent
  design_ref: null
  difference: design-doc.md:267 幂等 adopted vs CLI 裸 FileExistsError traceback
  finding_id: INC-004
  id: INC-004
  impact: CLI 可用性
  kind: inconsistency
  recommendation: fix_impl：CLI 前置 manifest 检查幂等打印退出
  severity: warning
  status: fixed
- analysis: 实现为有意增强未回写设计；测试宽松 match 不受影响
  classification: ambiguous
  code_ref: null
  confidence: medium
  decision: fix_design
  decision_note: 用户裁定：本轮 fix_design——design-doc 半初始化错误文案更新为实现实际模板（含绝对路径与 manifest
    缺失说明）
  design_ref: null
  difference: 设计字面文案 vs 实现增强文案（信息更全）
  finding_id: INC-005
  id: INC-005
  impact: 错误文案契约
  kind: inconsistency
  recommendation: fix_design：更新设计文案为实际模板
  severity: warning
  status: decided
triage_counts:
  by_classification:
    ambiguous: 3
    design_gap: 4
    impl_bug: 2
  open: 0
  total: 9
---

# 一致性检查报告 (b7c9e084-01)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 5 |
| 匹配项 | 11 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | - | logic | design-doc.md:302 | vinw/server.py:1809 | 设计 L1 gate 文案加（含现状摸底确认）；实现未触碰 gate_before_leave | work_mode 分支对 L1 追加 gate 后缀 |
| INC-002 | - | logic | design-doc.md:303 | vinw/server.py:1868-1872 | 设计 L4 work '加' Modify existing code in place；实现整体替换丢弃绿地条目；special_instruction 全层生效偏离 '其他层不变' | 追加 + special 按层收窄，或修订设计 |
| INC-003 | - | interface | api-design.md:1366 | vinw/server.py:271-272 | 设计守卫拒绝响应含 hint；not-found/not-a-dir 分支无 hint（设计内部不一致：守卫表只写 error） | 改设计标 hint 可选，或补通用 hint |
| INC-004 | - | logic | design-doc.md:267 | vinw/__main__.py:98-107 | 幂等 adopted 契约在 CLI 侧未实现：FileExistsError 裸 traceback | CLI adopt 前置 manifest 检查，幂等打印退出 |
| INC-005 | - | constraint | design-doc.md:268 | vinw/store/project.py:199-201 | 半初始化错误文案：设计字面值 vs 实现增强版（绝对路径+manifest 缺失说明） | 统一文案（倾向更新设计） |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| design-doc.md:269 | vinw/store/project.py:202-213 | Project.adopt/AdoptError.conflicts | 冲突守卫+conflicts+子目录 hint 一致 |
| design-doc.md:270 | vinw/store/project.py:291 | Project._scaffold | 空层目录复用 + 测试通过 |
| design-doc.md:272-278 | vinw/store/project.py:220-222 | manifest 字段 | work_mode/code_root/adopted_at 仅 adopt 写入，测试断言 |
| design-doc.md:284 | vinw/store/project.py:235-243 | changelog adopt | adopt 条目+测试断言 |
| design-doc.md:306-318 | vinw/store/project.py:151-161,228-231 | ADOPT_TODO_SECTION | L1 摸底种子+占位符消失，测试通过 |
| api-design.md:1353 | vinw/server.py:215-221 | se_init_project 签名 | adopt_existing 追加参数，工具数 40 不变，契约测试通过 |
| api-design.md:1364 | vinw/server.py:274-287 | adopt 响应 | adopted_existing/work_mode/code_root 齐备+测试 |
| api-design.md:1366 | vinw/server.py:260-270 | AdoptError 响应 | conflicts+hint，拒绝零写入+测试 |
| design-doc.md:300-302 | vinw/server.py:1861-1867 | next_steps L1 引导 | 摸底清单替换+测试（gate 后缀缺失见 INC-001） |
| design-doc.md:289 | vinw/server.py:288-300 | 兼容红线 | 366 测试全绿，默认路径逐字节不变 |
| design-doc.md:296 | vinw/__main__.py:44-50,104-107,123 | CLI --adopt-existing | flag+成功输出；测试缺失见 GAP-004/INC-004 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->