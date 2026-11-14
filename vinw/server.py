"""MCP Server — SE-MCP v2 tools registration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

import frontmatter

from .store.project import Project, LAYERS, has_placeholder_todo
from .store.registry import ProjectRegistry, ProjectNotFound
from .store.document import DocumentStore
from .workflow.state_machine import (
    AuditEscalationError,
    ConsistencyConfigError,
    ConsistencyGateError,
    LLMAuditRequiredError,
    PlaceholderTodoError,
    ToolingDiscrepancyError,
    WorkflowEngine,
)
from .workflow.consistency_llm import LLMConsistencyAuditor, TextConsistencyChecker
from .workflow.consistency_gate import ConsistencyGate
from .workflow.drift import detect_drift
from .workflow.triage import (
    CLASSIFICATIONS,
    DECISIONS,
    AuditTriage,
    TriageError,
)

# Gate types whose purpose is to stop work until a human approves
DESIGN_REVIEW_GATES = {"requirement-decomposition", "interface-design"}
from .workflow.search import ProposalSearcher

mcp = MCPServer("vinw")

# Global active project handle (simplified; production uses project_id mapping)
_active_project: Project | None = None


def _try_load_bootstrap_project() -> Project | None:
    """Bootstrap: auto-load a VINW project from the current working directory.

    Supports two layouts:
    - cwd itself is a project (cwd/.vinw/manifest.md)
    - cwd is a code repo containing a design project (cwd/vinw-design/.vinw/manifest.md)

    This lets VINW host itself: run `vinw server` inside the repo and the
    design project under vinw-design/ becomes the active project.
    """
    for candidate in (Path.cwd() / "vinw-design", Path.cwd()):
        if (candidate / ".vinw" / "manifest.md").exists():
            return Project(candidate)
    return None


# Self-hosting bootstrap: pick up an existing project at server startup.
_active_project = _try_load_bootstrap_project()


def _ensure_project() -> Project:
    if _active_project is None:
        raise RuntimeError("No active project. Call se_init_project first.")
    return _active_project


_registry: ProjectRegistry | None = None


def _get_registry() -> ProjectRegistry:
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry


def _consistency_state(proj) -> dict | None:
    state = proj.read_manifest().get("layer_states", {}).get("L4-编码实现", {}).get(
        "consistency"
    )
    if state is None:
        return None
    try:
        gate = ConsistencyGate(proj)
        llm = gate.llm_status()
        return {
            **state,
            "policy": llm["policy"],
            "needs_llm": not llm["satisfied"],
            "llm_verdict": state.get("llm_verdict"),
        }
    except Exception:
        return state


def _split_pending(pending: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split unresolved gates into blocking and review-only, oldest first."""
    now = datetime.now(timezone.utc)
    blocking: list[dict] = []
    review: list[dict] = []

    for item in pending:
        if item.get("resolved_at"):
            continue
        summary = {
            "id": item.get("id"),
            "layer": item.get("layer"),
            "descent": item.get("descent"),
            "item_type": item.get("item_type"),
            "description": item.get("description"),
        }
        proposed = item.get("proposed_at")
        if proposed:
            try:
                age = now - datetime.fromisoformat(proposed)
                summary["age_days"] = round(age.total_seconds() / 86400, 1)
            except (ValueError, TypeError):
                pass
        (blocking if item.get("blocking", True) else review).append(summary)

    return blocking, review


def _project_or_error(project: str | None) -> tuple[Project | None, str | None]:
    """Resolve a tool's optional `project` argument.

    None  -> the active project (bootstrap/adopt behaviour, unchanged)
    value -> registry resolution by path or registered name; _active_project
             is left untouched so per-call addressing never has side effects.
    """
    if project:
        try:
            resolved = _get_registry().resolve(project)
        except ProjectNotFound as e:
            return None, json.dumps(
                {
                    "error": str(e),
                    "available_projects": _get_registry().describe(),
                },
                ensure_ascii=False,
                indent=2,
            )
        _get_registry().touch(str(resolved.root))
        return resolved, None

    try:
        return _ensure_project(), None
    except RuntimeError as e:
        return None, json.dumps({"error": str(e)}, ensure_ascii=False)


# ── Project lifecycle ───────────────────────────────────────

@mcp.tool()
def se_init_project(name: str, path: str, description: str = "") -> str:
    """Initialize a new project with 7-layer spiral-ascend structure.

    If the target already contains a VINW project (.vinw/manifest.md), adopt it
    as the active project instead of re-initializing.
    """
    global _active_project
    root = Path(path).expanduser().resolve() / name
    if (root / ".vinw" / "manifest.md").exists():
        _active_project = Project(root)
        manifest = _active_project.read_manifest()
        return json.dumps(
            {
                "project_id": str(root),
                "adopted": True,
                "layers": LAYERS,
                "current_layer": manifest.get("current_layer", LAYERS[0]),
                "current_descent": manifest.get("current_descent", 1),
            },
            ensure_ascii=False,
            indent=2,
        )
    _active_project = Project.init(root, name, description)
    return json.dumps(
        {
            "project_id": str(root),
            "layers": LAYERS,
            "current_layer": "L1-需求拆解",
            "current_descent": 1,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def se_get_project(project: str | None = None) -> str:
    """Get full project state including layer graph and ascent history."""
    proj, err = _project_or_error(project)
    if err:
        return err
    manifest = proj.read_manifest()

    layer_states = manifest.get("layer_states", {})
    layer_graph = []
    for layer in LAYERS:
        state = layer_states.get(layer, {})
        layer_graph.append(
            {
                "layer": layer,
                "status": state.get("status", "pending"),
                "baseline": state.get("latest_baseline"),
                "descent_count": state.get("descent_count", 0),
                "superseded_by": state.get("superseded_by"),
                "active_ascent": state.get("active_ascent"),
            }
        )

    blocking_pending, pending_review = _split_pending(
        manifest.get("pending_confirmations", [])
    )

    return json.dumps(
        {
            "name": manifest.get("name"),
            "current_layer": manifest.get("current_layer"),
            "current_descent": manifest.get("current_descent"),
            "layer_graph": layer_graph,
            "ascent_history": manifest.get("ascent_history", []),
            "blocking_pending": blocking_pending,
            "pending_review": pending_review,
            "consistency": _consistency_state(proj),
            "drift": detect_drift(proj),
            "pending_confirmations": manifest.get("pending_confirmations", []),
        },
        ensure_ascii=False,
        indent=2,
    )


# ── Baseline ────────────────────────────────────────────────

@mcp.tool()
def se_baseline(layer: str, reason: str = "", force: bool = False, project: str | None = None) -> str:
    """Freeze specified layer as a baseline snapshot.

    Refuses when the layer's todo list is still the template placeholder,
    unless force=True.
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    engine = WorkflowEngine(proj)
    try:
        result = engine.baseline(layer, reason, force=force)
    except PlaceholderTodoError as e:
        return json.dumps(
            {
                "error": str(e),
                "hint": "调用 se_update_todo 填写真实待办，或传 force=true",
            },
            ensure_ascii=False,
            indent=2,
        )
    except ConsistencyGateError as e:
        return json.dumps(
            {
                "error": str(e),
                "hint": "查看 L4-编码实现/consistency-reports/ 最新报告修复不一致；"
                        "若确认可跳过，传 force=true",
                "consistency": _consistency_state(proj),
            "drift": detect_drift(proj),
            },
            ensure_ascii=False,
            indent=2,
        )
    except LLMAuditRequiredError as e:
        return json.dumps(
            {
                "error": str(e),
                "hint": "用独立 reviewer 执行 se_check_consistency(method=\"llm\") 的提示词，"
                        "再以 se_store_consistency_report 提交结论（auditor=reviewer）",
                "consistency": _consistency_state(proj),
            "drift": detect_drift(proj),
            },
            ensure_ascii=False,
            indent=2,
        )
    except ToolingDiscrepancyError as e:
        return json.dumps(
            {
                "error": str(e),
                "hint": "疑似提取器缺陷：核对 vinw/workflow/symbols.py 的规则，"
                        "修正后重跑；或显式 force=true",
                "consistency": _consistency_state(proj),
            "drift": detect_drift(proj),
            },
            ensure_ascii=False,
            indent=2,
        )
    except AuditEscalationError as e:
        return json.dumps(
            {
                "error": str(e),
                "hint": "用 se_get_escalations 查看差异点/分析/推荐，"
                        "se_record_triage_decision 裁决后重试",
                "escalations": AuditTriage(proj).escalations(),
            },
            ensure_ascii=False,
            indent=2,
        )
    except ConsistencyConfigError as e:
        return json.dumps(
            {
                "error": str(e),
                "hint": "检查 manifest 的 code_extensions / code_root 与 code_scope",
                "consistency": _consistency_state(proj),
            "drift": detect_drift(proj),
            },
            ensure_ascii=False,
            indent=2,
        )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def se_list_baselines(layer: str = "", project: str | None = None) -> str:
    """List baselines for a layer (or all layers if empty)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    layers_to_check = [layer] if layer else LAYERS
    result = {}
    for l in layers_to_check:
        result[l] = proj.list_baselines(l)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Ascend / Descend ────────────────────────────────────────

@mcp.tool()
def se_ascend(from_layer: str, to_layer: str, to_baseline: str, reason: str, project: str | None = None) -> str:
    """
    Ascend (rollback) from from_layer to to_layer's specified baseline.
    Triggers a new descent round; lower layers become superseded.
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    engine = WorkflowEngine(proj)
    try:
        result = engine.ascend(from_layer, to_layer, to_baseline, reason)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def se_descend(to_layer: str, reason: str = "", project: str | None = None) -> str:
    """Descend from current layer to a lower layer."""
    proj, err = _project_or_error(project)
    if err:
        return err
    engine = WorkflowEngine(proj)
    try:
        result = engine.descend(to_layer, reason)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def se_can_descend(project: str | None = None) -> str:
    """Check if current layer can safely descend to next layer."""
    proj, err = _project_or_error(project)
    if err:
        return err
    engine = WorkflowEngine(proj)
    ok, msg, next_layer = engine.can_descend_to_next()
    return json.dumps(
        {"can_descend": ok, "message": msg, "next_layer": next_layer},
        ensure_ascii=False,
    )


# ── Confirmations ───────────────────────────────────────────

@mcp.tool()
def se_require_confirmation(
    item_type: str,
    description: str,
    options: str = '["approve","reject","modify"]',
    blocking: bool | None = None,
    project: str | None = None,
) -> str:
    """Create a confirmation gate item.

    Design-review gates (requirement-decomposition, interface-design) block by
    default because their purpose is to stop the work; other types are review
    notices and default to non-blocking. Pass `blocking` to override.
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    if blocking is None:
        blocking = item_type in DESIGN_REVIEW_GATES
    engine = WorkflowEngine(proj)
    opts = json.loads(options)
    cfm_id = engine.require_confirmation(item_type, description, opts, blocking)
    return json.dumps({"confirmation_id": cfm_id, "status": "pending"}, ensure_ascii=False)


@mcp.tool()
def se_resolve_confirmation(confirmation_id: str, resolution: str, feedback: str = "", project: str | None = None) -> str:
    """Resolve a pending confirmation (approve/reject/modify)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    engine = WorkflowEngine(proj)
    try:
        result = engine.resolve_confirmation(confirmation_id, resolution, feedback)
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ── Document CRUD ───────────────────────────────────────────

@mcp.tool()
def se_store_document(layer: str, filename: str, content: str, doc_type: str = "generic", project: str | None = None) -> str:
    """Store/update a document in a layer directory."""
    proj, err = _project_or_error(project)
    if err:
        return err
    path = proj.write_document(layer, filename, content, doc_type=doc_type)
    return json.dumps({"path": str(path), "status": "stored"}, ensure_ascii=False)


@mcp.tool()
def se_read_document(layer: str, filename: str, project: str | None = None) -> str:
    """Read a layer document (returns frontmatter + content)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    try:
        doc = proj.read_document(layer, filename)
        return json.dumps(doc, ensure_ascii=False, indent=2)
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def se_list_documents(layer: str = "", project: str | None = None) -> str:
    """List documents in a layer (or all layers)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    store = DocumentStore(proj)
    layers_to_check = [layer] if layer else LAYERS
    result = {}
    for l in layers_to_check:
        files = store.list_layer_files(l)
        result[l] = [f.name for f in files]
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Changelog ───────────────────────────────────────────────

@mcp.tool()
def se_log_change(
    change_type: str, scope: str, reason: str, before: str = "", after: str = "",
    project: str | None = None,
) -> str:
    """Atomically log a change (must be called BEFORE actual modification)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    manifest = proj.read_manifest()
    descent = manifest.get("current_descent", 1)
    layer = manifest.get("current_layer", LAYERS[0])

    from .store.changelog import append_changelog_entry

    change_id = append_changelog_entry(
        proj.vinw_dir / "changelog.md",
        change_type=change_type,
        layer=layer,
        descent=descent,
        scope=scope,
        reason=reason,
        before=before,
        after=after,
    )
    return json.dumps({"change_id": change_id}, ensure_ascii=False)


@mcp.tool()
def se_get_changelog(limit: int = 20, project: str | None = None) -> str:
    """Return recent changelog entries."""
    proj, err = _project_or_error(project)
    if err:
        return err
    path = proj.vinw_dir / "changelog.md"
    if not path.exists():
        return json.dumps({"entries": []}, ensure_ascii=False)

    content = path.read_text(encoding="utf-8")
    # Split by chg- headers
    import re

    entries = re.split(r"\n## (chg-\S+)", content)
    # entries[0] is preamble, then pairs of (id, body)
    parsed = []
    for i in range(1, len(entries), 2):
        parsed.append({"id": entries[i], "body": entries[i + 1].strip()})

    return json.dumps({"entries": parsed[-limit:][::-1]}, ensure_ascii=False, indent=2)


# ── Consistency check ───────────────────────────────────────

@mcp.tool()
def se_check_consistency(
    design_layer: str = "L3-方案细化",
    design_doc: str = "api-design.md",
    code_scope: str = "[]",
    method: str = "llm",
    project: str | None = None,
) -> str:
    """
    Check document-code consistency.
    
    method="llm": Use LLM semantic audit (returns prompt for agent to call LLM)
    method="text": Local text-based existence check (no LLM required)
    method="ast": tree-sitter structured comparison (fallback to llm for now)
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    scope = json.loads(code_scope)

    if method == "llm" or method == "ast":
        gate = ConsistencyGate(proj)
        freshness = gate.freshness(scope or None)
        if freshness["state"] == "fresh":
            report = freshness["report"] or {}
            return json.dumps(
                {
                    "reused": True,
                    "reason": "代码与设计自上次通过的报告后未改动，复用结论",
                    "report_id": report.get("report_id"),
                    "overall": report.get("overall_status"),
                    "checked_at": report.get("checked_at"),
                    "changed": [],
                    "note": "如需强制重审，先修改文件或删除该报告后重试",
                },
                ensure_ascii=False,
                indent=2,
            )
        auditor = LLMConsistencyAuditor(proj)
        result = auditor.audit(design_layer, design_doc, scope or None)
        result["freshness"] = {
            "state": freshness["state"],
            "changed": freshness.get("changed", []),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif method == "text":
        checker = TextConsistencyChecker(proj)
        result = checker.check(design_layer, design_doc, scope or None)
        result["note"] = "Use method='llm' for full semantic audit with report storage"
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"error": f"Unknown method: {method}"}, ensure_ascii=False)


@mcp.tool()
def se_store_consistency_report(
    report_json: str,
    auditor: str = "",
    auditor_model: str = "",
    project: str | None = None,
) -> str:
    """Store a parsed LLM consistency report (call after getting LLM response).

    The report is recorded with kind="llm" plus auditor identity, so later
    gates can require and trace semantic review.
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    llm_auditor = LLMConsistencyAuditor(proj)
    report_data = json.loads(report_json)
    if not auditor:
        # manifest.consistency_auditor declares the expected reviewer type
        auditor = str(
            proj.read_manifest().get("consistency_auditor") or "reviewer"
        )
    gate = ConsistencyGate(proj)
    descent_now = proj.read_manifest().get("current_descent", 1)
    fingerprint = gate.current_fingerprint()

    report_path = llm_auditor.store_report(
        report_data,
        descent=descent_now,
        design_digest=fingerprint["design_hash"],
        hashes=fingerprint["file_hashes"],
        kind="llm",
        policy=gate.policy(),
        auditor=auditor,
        auditor_model=auditor_model or None,
    )
    gate.record_llm_state(frontmatter.load(report_path).metadata)
    return json.dumps(
        {"report_path": str(report_path), "status": "stored"},
        ensure_ascii=False,
    )


# ── Proposal search ─────────────────────────────────────────

@mcp.tool()
def se_search_proposals(
    query: str,
    search_scope: str = "local",
    method: str = "rg",
    archive_dir: str = "",
    top_k: int = 10,
    project: str | None = None,
) -> str:
    """
    Search for similar proposals across project documents.
    
    scope="local": Search within current project's layer docs
    scope="archive": Search in specified archive directory
    method="rg": ripgrep text search (default, zero cost)
    method="tfidf": TF-IDF cosine similarity (needs sklearn)
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    searcher = ProposalSearcher(proj)
    result = searcher.search(
        query=query,
        scope=search_scope,
        method=method,
        archive_dir=archive_dir or None,
        top_k=top_k,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Todo management ─────────────────────────────────────────

@mcp.tool()
def se_get_todos(project: str | None = None) -> str:
    """Get all todos across layers (excluding superseded layers)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    todos = proj.get_todos()
    return json.dumps(todos, ensure_ascii=False, indent=2)


@mcp.tool()
def se_update_todo(layer: str, todos_json: str, project: str | None = None) -> str:
    """Update todo list in a layer's README.md."""
    proj, err = _project_or_error(project)
    if err:
        return err
    readme_path = proj.get_layer_dir(layer) / "README.md"
    if not readme_path.exists():
        return json.dumps({"error": f"{layer}/README.md not found"}, ensure_ascii=False)

    post = frontmatter.load(readme_path)
    content = post.content

    import re

    todo_section = "## 当前待办\n\n"
    todos = json.loads(todos_json)
    for t in todos:
        checkbox = "[x]" if t.get("done") else "[ ]"
        todo_section += f"- {checkbox} {t['text']}\n"

    pattern = r"(## 当前待办\n\n(?:- \[[ xX]\].*\n)*)"
    if re.search(pattern, content):
        new_content = re.sub(pattern, todo_section, content)
    else:
        new_content = content.rstrip() + "\n\n" + todo_section

    post.content = new_content
    post.metadata["todo_descent"] = proj.read_manifest().get("current_descent", 1)
    readme_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return json.dumps({"layer": layer, "todo_count": len(todos)}, ensure_ascii=False)


@mcp.tool()
def se_purge_confirmations(
    before_descent: int = 0, resolution: str = "superseded",
    project: str | None = None,
) -> str:
    """
    Settle unresolved confirmations left over from earlier descent rounds.

    before_descent=0 settles anything older than the current descent.
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    engine = WorkflowEngine(proj)
    result = engine.purge_confirmations(before_descent, resolution)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Project completion ──────────────────────────────────────


@mcp.tool()
def se_complete_project(project: str | None = None) -> str:
    """
    Mark the project as completed (L7 final acceptance closure).

    Prerequisites: current layer is L7-终验, L1-L6 all baselined, and no
    unresolved blocking confirmations. On success, L7 README is marked
    completed and the manifest records completed_at.
    """
    proj, err = _project_or_error(project)
    if err:
        return err
    manifest = proj.read_manifest()

    errors: list[str] = []
    current = manifest.get("current_layer")
    if current != "L7-终验":
        errors.append(f"当前层为 {current}，必须为 L7-终验")

    layer_states = manifest.get("layer_states", {})
    for layer in LAYERS[:-1]:
        state = layer_states.get(layer, {})
        if state.get("status") != "baselined":
            errors.append(
                f"{layer} 未基线化（status={state.get('status', 'pending')}）"
            )

    # Placeholder todos mean the layer was never really worked on
    for layer in LAYERS:
        readme = proj.read_layer_readme(layer)
        if has_placeholder_todo(readme.get("content", "")):
            errors.append(
                f"{layer} 待办仍为模板占位符，请用 se_update_todo 填写真实待办"
            )

    pending = manifest.get("pending_confirmations", [])
    unresolved = [
        p for p in pending if p.get("blocking", True) and not p.get("resolved_at")
    ]
    if unresolved:
        errors.append(
            f"{len(unresolved)} 个未解决的 blocking 门控: "
            f"{[p['id'] for p in unresolved]}"
        )

    gate = ConsistencyGate(proj)
    descent_now = manifest.get("current_descent", 1)
    passing = gate.latest_passing(descent_now)
    if passing is None:
        errors.append(
            f"本轮（descent-{descent_now}）缺少通过的一致性检查报告："
            "请调用 se_check_consistency 后重试"
        )
    else:
        llm = gate.llm_status(descent_now)
        if llm["required"] and not llm["present"]:
            errors.append(
                f"策略 {llm['policy']} 要求本轮 LLM 语义审核结论，尚未提供"
                "（se_store_consistency_report 提交 reviewer 结论后重试）"
            )
        disc = gate.discrepancy(descent_now)
        if disc is not None:
            errors.append(f"text 与 LLM 结论冲突：{disc['reason']}")
        triage = AuditTriage(proj).decision()
        if triage["decision"] == "escalate":
            errors.append(
                f"{len(triage.get('escalations', []))} 条审计发现待人工裁定"
                "（se_get_escalations 查看）"
            )
        elif triage["decision"] == "auto_fix_pending":
            errors.append(
                f"{len(triage.get('auto_fixable', []))} 条高置信实现缺陷待修正"
            )

    if errors:
        return json.dumps(
            {"error": "完成前置条件未满足", "details": errors},
            ensure_ascii=False,
            indent=2,
        )

    engine = WorkflowEngine(proj)
    # Stale non-blocking gates from earlier rounds are settled, not blocking
    purged = engine.purge_confirmations(only_non_blocking=True)
    engine.mark_layer_completed("L7-终验")

    manifest = proj.read_manifest()
    layer_states = manifest.get("layer_states", {})
    layer_states.setdefault("L7-终验", {})["status"] = "completed"
    completed_at = datetime.now(timezone.utc).isoformat()
    manifest["layer_states"] = layer_states
    manifest["completed_at"] = completed_at
    proj.write_manifest(manifest)

    from .store.changelog import append_changelog_entry

    append_changelog_entry(
        proj.vinw_dir / "changelog.md",
        change_type="complete",
        layer="L7-终验",
        descent=manifest.get("current_descent", 1),
        scope="project",
        reason="项目终验完成",
    )

    return json.dumps(
        {
            "status": "completed",
            "completed_at": completed_at,
            "purged_confirmations": purged.get("ids", []),
            "pending_review": _split_pending(
                proj.read_manifest().get("pending_confirmations", [])
            )[1],
        },
        ensure_ascii=False,
        indent=2,
    )


# ── Multi-project registry tools ────────────────────────────


@mcp.tool()
def se_register_project(path: str, name: str = "") -> str:
    """Register an existing VINW project (must contain .vinw/manifest.md)."""
    try:
        result = _get_registry().add(path, name or None)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def se_list_projects(status: str = "") -> str:
    """List registered projects with live status (ok/missing); never deletes."""
    projects = _get_registry().list(status=status or None)
    return json.dumps(
        {"count": len(projects), "projects": projects}, ensure_ascii=False, indent=2
    )


@mcp.tool()
def se_remove_project(project: str) -> str:
    """Remove a project registration (disk content is never touched)."""
    try:
        result = _get_registry().remove(project)
    except ProjectNotFound as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def se_set_project_state(project: str, state: str) -> str:
    """Declare a project active or dormant (intent; affects probing cost)."""
    try:
        result = _get_registry().set_state(project, state)
    except (ProjectNotFound, ValueError) as e:
        return json.dumps(
            {"error": str(e), "available_projects": _get_registry().describe()},
            ensure_ascii=False,
            indent=2,
        )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def se_project_history(project: str, limit: int = 20) -> str:
    """Show a project's state-transition log (register/activate/missing/...)."""
    try:
        entries = _get_registry().history(project, limit)
    except ProjectNotFound as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    return json.dumps(
        {"project": project, "count": len(entries), "events": entries},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def se_export_projects() -> str:
    """Export the registry as a JSON snapshot (readable/backup, not read back)."""
    return json.dumps(_get_registry().export_json(), ensure_ascii=False, indent=2)


@mcp.tool()
def se_prune_projects(force: bool = False) -> str:
    """Drop registrations whose path no longer holds a VINW project.

    force=False (default) is a dry run that only reports candidates.
    """
    result = _get_registry().prune(missing_only=True, force=force)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def se_use_project(project: str) -> str:
    """Make a project active so subsequent tools can omit `project`."""
    global _active_project
    try:
        resolved = _get_registry().resolve(project)
    except ProjectNotFound as e:
        return json.dumps(
            {"error": str(e), "available_projects": _get_registry().describe()},
            ensure_ascii=False,
            indent=2,
        )
    _active_project = resolved
    _get_registry().touch(str(resolved.root))
    manifest = resolved.read_manifest()
    return json.dumps(
        {
            "active": True,
            "name": manifest.get("name"),
            "path": str(resolved.root),
            "current_layer": manifest.get("current_layer"),
            "current_descent": manifest.get("current_descent"),
        },
        ensure_ascii=False,
        indent=2,
    )


# ── Audit triage (L3 v0.12) ─────────────────────────────────


@mcp.tool()
def se_triage_prompt(project: str | None = None) -> str:
    """Return the triage instructions plus the findings awaiting judgement."""
    proj, err = _project_or_error(project)
    if err:
        return err

    triage = AuditTriage(proj)
    latest = triage.latest_llm_report()
    findings = triage.findings()

    instructions = (
        "对每条发现先判断『设计本身是否合理』，再判断『实现是否偏离设计』：\n"
        "1. 设计不合理/过时/自相矛盾 → design_bug 或 design_gap\n"
        "2. 设计合理而实现偏离       → impl_bug\n"
        "3. 涉及外部契约、命名偏好、优先级权衡 → ambiguous\n"
        "4. confidence=high 必须给出明确证据（行号+推理链），否则降为 medium\n"
        "禁止默认把不一致判为 impl_bug。\n\n"
        "输出 JSON：{\"triage\":[{\"id\":..., \"classification\":"
        "\"impl_bug|design_bug|design_gap|ambiguous\", \"confidence\":"
        "\"high|medium|low\", \"difference\":\"设计侧 vs 代码侧\", "
        "\"analysis\":\"为什么可能是实现错/设计错\", \"recommendation\":\"...\", "
        "\"impact\":\"影响面\"}]}"
    )

    return json.dumps(
        {
            "instructions": instructions,
            "report_id": latest[0] if latest else None,
            "findings": findings,
            "classifications": list(CLASSIFICATIONS),
            "decisions": list(DECISIONS),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def se_store_triage(report_json: str, project: str | None = None) -> str:
    """Attach triage verdicts to the latest LLM audit report."""
    proj, err = _project_or_error(project)
    if err:
        return err
    try:
        result = AuditTriage(proj).store(json.loads(report_json))
    except (TriageError, json.JSONDecodeError) as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def se_get_escalations(project: str | None = None) -> str:
    """List findings that need a human decision (difference/analysis/recommendation)."""
    proj, err = _project_or_error(project)
    if err:
        return err
    triage = AuditTriage(proj)
    decision = triage.decision()
    return json.dumps(
        {
            "decision": decision.get("decision"),
            "count": len(decision.get("escalations", []) or []),
            "escalations": decision.get("escalations", []),
            "auto_fixable": decision.get("auto_fixable", []),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def se_record_triage_decision(
    finding_id: str, decision: str, note: str = "", project: str | None = None
) -> str:
    """Record a human decision for one escalated finding."""
    proj, err = _project_or_error(project)
    if err:
        return err
    try:
        result = AuditTriage(proj).record_decision(finding_id, decision, note)
    except TriageError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Guidance ────────────────────────────────────────────────

@mcp.tool()
def se_get_next_steps(project: str | None = None) -> str:
    """Get recommended next actions based on current layer state."""
    proj, err = _project_or_error(project)
    if err:
        return err
    manifest = proj.read_manifest()
    current = manifest.get("current_layer")
    descent = manifest.get("current_descent")
    pending = manifest.get("pending_confirmations", [])
    layer_states = manifest.get("layer_states", {})
    state = layer_states.get(current, {})

    blocking_pending, pending_review = _split_pending(pending)
    if blocking_pending:
        return json.dumps(
            {
                "current_layer": current,
                "descent": descent,
                "status": "awaiting_confirmation",
                "actions": [
                    f"Resolve blocking gate {u['id']} ({u['item_type']}): "
                    f"{u['description'][:60]}"
                    for u in blocking_pending
                ],
                "awaiting_review": pending_review,
                "suggested_tools": ["se_resolve_confirmation"],
            },
            ensure_ascii=False,
            indent=2,
        )

    suggestions: dict[str, dict[str, Any]] = {
        "L1-需求拆解": {
            "work": ["Decompose requirements → proposals.md", "Identify key problem domains"],
            "gate": "se_require_confirmation(requirement decomposition conclusion)",
            "next_action": "se_baseline(L1) → se_descend(L2)",
        },
        "L2-参考文献与方案搜证汇总": {
            "work": [
                "Search references → references.md",
                "Collect existing solutions → references.md",
                "Build evidence matrix → evidence-matrix.md",
                "Synthesize conclusions → synthesis.md",
            ],
            "gate": "se_require_confirmation(evidence synthesis & recommended direction)",
            "next_action": "se_baseline(L2) → se_descend(L3)",
            "special": "If evidence reveals requirement bias, se_ascend(L2→L1, baseline, reason)",
        },
        "L3-方案细化": {
            "work": [
                "Refine design based on L2/synthesis.md → design-doc.md",
                "Interface design → api-design.md",
            ],
            "gate": "se_require_confirmation(interface design)",
            "next_action": "se_baseline(L3) → se_descend(L4)",
        },
        "L4-编码实现": {
            "work": ["Implement code", "se_check_consistency(code vs design)"],
            "gate": "Consistency check passed",
            "next_action": "se_log_change(per modification) → se_baseline(L4) → se_descend(L5)",
        },
        "L5-测试验证": {
            "work": ["Write/execute tests", "Record test results", "Analyze root cause if defects found"],
            "gate": "se_require_confirmation(test results)",
            "special": "If design-level defects found, call se_ascend(L5→L2/L1, baseline, reason) to trigger ascent",
            "next_action": "se_baseline(L5), or ascend for redesign",
        },
        "L6-检视清理": {
            "work": ["Remove debug code", "Sync documents", "Clean logs"],
            "next_action": "se_baseline(L6) → se_descend(L7)",
        },
        "L7-终验": {
            "work": ["Final report", "Project archive"],
            "next_action": "Project complete",
        },
    }

    s = suggestions.get(current, {})
    engine = WorkflowEngine(proj)
    can_desc, desc_msg, next_layer = engine.can_descend_to_next()

    return json.dumps(
        {
            "current_layer": current,
            "descent": descent,
            "layer_status": state.get("status"),
            "suggested_work": s.get("work", []),
            "gate_before_leave": s.get("gate"),
            "can_descend": can_desc,
            "descend_message": desc_msg,
            "next_layer": next_layer,
            "special_instruction": s.get("special", ""),
            "awaiting_review": pending_review,
            "consistency": _consistency_state(proj),
            "drift": detect_drift(proj),
        },
        ensure_ascii=False,
        indent=2,
    )
