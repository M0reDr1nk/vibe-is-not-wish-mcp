---
auditor: reviewer
auditor_model: independent-subagent (r25 + r26 re-review)
checked_at: '2026-11-14T14:32:18.799849+00:00'
code_fingerprint: 924ed5e5ece6af42b389772d5ddb088b0bb4bf7b4211d35be0f4dafbee411200
code_symbols_count: 873
descent: 20
design_hash: 4d1cdcf44dbe84c46d7c3f0ca0bd09b0158ff804435a77e1ad27055435521708
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
  scripts/run_consistency_check.py: 0c54c40d27bb0647f2c7bbeb2e4e71a04f1ccda4509c230f0ac077c62a74de1a
  tests/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  tests/conftest.py: 55bce5036f8ee83ef6a3e5007907b923dd1df479ebf317dff0a9284e85d035f2
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
  vinw/__main__.py: 32873b6ef11a5dae903ceba8f0dd9114fd6703dd82f32d5acac26f999a0fd68d
  vinw/server.py: 95597ae5783e5dc4a9a3c5738e35e0430983a7567cb1b63d7b14941b79060c53
  vinw/store/__init__.py: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  vinw/store/changelog.py: 683940505c76078cc815bd236635e8a5f540a2f959442a26b4808497f739103e
  vinw/store/document.py: 7c5e44c5e9978f7d26b6fcdc5774111a68f1d4c220ce467520efbebdb52d82e8
  vinw/store/project.py: 84d09f15d687f1eddf358115971e54515c644304a22339f1efa989e83f75a8cc
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
files_scanned: 57
gaps:
- analysis: baseline(force=True) 完全跳过漂移门控，agent 可自批自过
  classification: impl_bug
  confidence: high
  description: force=True 可绕过待批准/已过期特例硬停
  design_ref: api-design.md:1303
  difference: pending/expired 仅在 heal_drift 内阻断，force 路径不调用 heal_drift
  id: GAP-001
  impact: 核心需求可被绕过
  missing: code
  recommendation: 硬停提到无条件前置守卫
  severity: critical
  status: fixed
- analysis: L4 基线是常见路径，可完整跳过违约后强制校验
  classification: impl_bug
  confidence: high
  description: AC8 标志写入耦合在 if log：L4 路径 heal_drift(log=False) 不写标志
  design_ref: api-design.md:1308
  difference: 设计要求首次容忍必写标志
  id: GAP-002
  impact: AC8 在 L4 路径失效
  missing: code
  recommendation: 标志写入移出 log 分支
  severity: critical
  status: fixed
- analysis: 两套实现已分叉，后续修复会埋雷
  classification: impl_bug
  confidence: high
  description: _guard_drift_exception 为死代码且副作用与 heal_drift 分叉
  design_ref: api-design.md:1270
  difference: 设计称三处共用
  id: GAP-003
  impact: 维护风险
  missing: code
  recommendation: 删除，保留单一实现
  severity: warning
  status: fixed
- analysis: expired 属 approved 未正规化
  classification: impl_bug
  confidence: high
  description: 完成态漏 expired，且特例异常未捕获（工具崩溃式报错）
  design_ref: api-design.md:1287
  difference: 设计要求完成态不得有未正规化特例
  id: GAP-004
  impact: 错误不可读
  missing: code
  recommendation: 守卫覆盖 expired + 异常转结构化
  severity: warning
  status: fixed
- analysis: 循环依赖使 expired 分支不可测/假测
  classification: design_gap
  confidence: high
  description: 期限机制在真实流程中不可达（descent 仅在 ascend 递增，而 ascend 会正规化）
  design_ref: api-design.md:1270
  difference: 设计承诺限期正规化
  id: GAP-005
  impact: 安全阀不生效
  missing: design
  recommendation: 增加使用次数触发过期
  severity: warning
  status: fixed
- analysis: 空 reason 或回退分支会错误匹配
  classification: impl_bug
  confidence: high
  description: 特例与确认无外键，按 reason 子串匹配，可能批准错的特例
  design_ref: api-design.md:1237
  difference: 设计称决议作用于对应特例
  id: GAP-006
  impact: 批准对象错位
  missing: code
  recommendation: 存 confirmation_id 并按 id 精确匹配 + 仅 pending
  severity: warning
  status: fixed
- analysis: MCP 工具调用方就是 agent，服务端无法辨别；与直接改 manifest 同类
  classification: design_gap
  confidence: high
  description: agent 可自行调用 se_resolve_confirmation 批准特例（协议层无法区分身份）
  design_ref: api-design.md:1303
  difference: 设计称 agent 不能自行批准
  id: GAP-007
  impact: 核心诉求在协议层不可强制
  missing: design
  recommendation: 明确威胁模型与已知限制，写入设计；靠 TUI 人类通道或一次性令牌才可能真正强制
  severity: critical
  status: accepted
- analysis: 两个 critical 未被契约测试捕获
  classification: impl_bug
  confidence: high
  description: 测试未覆盖 force 旁路/L4 log=False/完成态守卫/TUI 三态/关联失配
  design_ref: api-design.md:1308
  difference: 设计契约多路径，测试仅 happy path
  id: GAP-008
  impact: 回归无保护
  missing: test
  recommendation: 补 6 例加固测试
  severity: warning
  status: fixed
gaps_count: 8
inconsistencies:
- category: logic
  code_ref: state_machine.py:258
  description: 设计表格写 clean 时正常转换，实现 clean+pending/expired 硬停
  design_ref: api-design.md:1282
  id: INC-001
  severity: null
  suggestion: 文档补行
- category: data_model
  code_ref: server.py:1390
  description: design 称 approve 时写 deadline，实现 request 时写
  design_ref: api-design.md:1262
  id: INC-002
  severity: null
  suggestion: 文档改为 request 定死
- category: interface
  code_ref: state_machine.py:425
  description: 契约三态，实现返回四态（含 pending）
  design_ref: api-design.md:1270
  id: INC-003
  severity: null
  suggestion: 文档补 pending
- category: logic
  code_ref: state_machine.py:470
  description: 容忍动作两套实现且副作用不同（AC8 标志）
  design_ref: api-design.md:1283
  id: INC-004
  severity: null
  suggestion: 合并单一实现
- category: constraint
  code_ref: server.py:869
  description: complete 的 AC8 检查在 heal（可能首次写标志）之前，存在时序缺口
  design_ref: api-design.md:1308
  id: INC-005
  severity: null
  suggestion: heal 后复查
inconsistencies_count: 5
kind: llm
layer: L4-编码实现
llm_verdict: warning
overall_status: warning
policy: text+llm
report_id: a45825fa-01
se_version: '2.0'
triage:
- analysis: _assert_exception_hard_stop 前置到任何 force 分支之前
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 硬停前置，force 不可绕过
  design_ref: null
  difference: force 旁路
  finding_id: GAP-001
  id: GAP-001
  impact: 核心需求落实
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: AC8 标志与计数移入 _tolerate 无条件写
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: AC8 标志移出 log 分支
  design_ref: null
  difference: log 耦合
  finding_id: GAP-002
  id: GAP-002
  impact: L4 路径不再漏检
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已删除，单一实现
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 死代码删除
  design_ref: null
  difference: 死代码分叉
  finding_id: GAP-003
  id: GAP-003
  impact: 维护面
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 守卫覆盖三态 + 异常转结构化 JSON
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 完成守卫覆盖三态 + 结构化异常
  design_ref: null
  difference: 完成态漏 expired
  finding_id: GAP-004
  id: GAP-004
  impact: 错误可读
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 改为轮次或使用次数（max 3）任一触发
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 过期加使用次数条件
  design_ref: null
  difference: 期限不可达
  finding_id: GAP-005
  id: GAP-005
  impact: 安全阀真实生效
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: confirmation_id 写回 + 按 id 精确匹配 + 仅 pending
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: confirmation_id 外键 + 仅 pending
  design_ref: null
  difference: 无外键
  finding_id: GAP-006
  id: GAP-006
  impact: 批准对象正确
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已写入设计作为已知限制；缓解=双向 changelog 审计痕迹
  classification: design_gap
  code_ref: null
  confidence: high
  decision: accept_as_is
  decision_note: 协议层限制已记录，需宿主层强制
  design_ref: null
  difference: 协议层无法区分 agent/人
  finding_id: GAP-007
  id: GAP-007
  impact: 需宿主层才能真正强制
  kind: inconsistency
  recommendation: accept_as_is
  severity: warning
  status: accepted
- analysis: 已补 6 例加固用例（354 总计）
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: +6 加固用例
  design_ref: null
  difference: 测试缺口
  finding_id: GAP-008
  id: GAP-008
  impact: 回归保护
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已补 clean/unknown + pending/expired 行
  classification: design_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 门控表补硬停行
  design_ref: null
  difference: 表格缺硬停行
  finding_id: INC-001
  id: INC-001
  impact: 契约明确
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 设计统一为 request 定死
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: deadline 时机统一
  design_ref: null
  difference: deadline 写入时机
  finding_id: INC-002
  id: INC-002
  impact: 低
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 伪代码与表格已更新为四态
  classification: design_gap
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 四态文档已更新
  design_ref: null
  difference: 三态 vs 四态
  finding_id: INC-003
  id: INC-003
  impact: 契约一致
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 已合并为 _tolerate
  classification: impl_bug
  code_ref: null
  confidence: high
  decision: fix_impl
  decision_note: 容忍逻辑合并
  design_ref: null
  difference: 两套容忍实现
  finding_id: INC-004
  id: INC-004
  impact: 无埋雷
  kind: inconsistency
  recommendation: fixed
  severity: warning
  status: fixed
- analysis: 当前被 pending/active 守卫掩盖；记录为结构性防御项
  classification: impl_bug
  code_ref: null
  confidence: medium
  decision: accept_as_is
  decision_note: 当前被守卫掩盖，记为结构性防御项
  design_ref: null
  difference: complete 校验顺序
  finding_id: INC-005
  id: INC-005
  impact: 潜在
  kind: inconsistency
  recommendation: accept_as_is
  severity: warning
  status: accepted
triage_counts:
  by_classification:
    design_bug: 1
    design_gap: 3
    impl_bug: 9
  open: 0
  total: 13
---

# 一致性检查报告 (a45825fa-01)

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | warning |
| 不一致项 | 5 |
| 匹配项 | 5 |

## 不一致项

| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |
|----|---------|------|---------|---------|------|------|
| INC-001 | - | logic | api-design.md:1282 | state_machine.py:258 | 设计表格写 clean 时正常转换，实现 clean+pending/expired 硬停 | 文档补行 |
| INC-002 | - | data_model | api-design.md:1262 | server.py:1390 | design 称 approve 时写 deadline，实现 request 时写 | 文档改为 request 定死 |
| INC-003 | - | interface | api-design.md:1270 | state_machine.py:425 | 契约三态，实现返回四态（含 pending） | 文档补 pending |
| INC-004 | - | logic | api-design.md:1283 | state_machine.py:470 | 容忍动作两套实现且副作用不同（AC8 标志） | 合并单一实现 |
| INC-005 | - | constraint | api-design.md:1308 | server.py:869 | complete 的 AC8 检查在 heal（可能首次写标志）之前，存在时序缺口 | heal 后复查 |


## 匹配项

| 设计引用 | 代码引用 | 符号 | 说明 |
|---------|---------|------|------|
| api-design.md:1328 | state_machine.py:459 | 硬停前置 | r26 复核：force 不能绕过 |
| api-design.md:1317 | state_machine.py:431 | _tolerate | r26 复核：AC8 标志无条件写 |
| api-design.md:1333 | server.py:1405 | confirmation_id 外键 | r26 复核：按 id 精确匹配且仅 pending |
| api-design.md:1332 | state_machine.py:418 | 过期判定 | r26 复核：轮次或使用次数 |
| api-design.md:1336 | tui/app.py:227 | TUI 三态 | r26 复核：已纳入使用次数 |


## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->