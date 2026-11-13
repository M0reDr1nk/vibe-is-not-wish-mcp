"""MCP Server — SE-MCP v2 tools registration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

import frontmatter

from .store.project import Project, LAYERS
from .store.document import DocumentStore
from .workflow.state_machine import WorkflowEngine
from .workflow.consistency_llm import LLMConsistencyAuditor, TextConsistencyChecker
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
def se_get_project() -> str:
    """Get full project state including layer graph and ascent history."""
    proj = _ensure_project()
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

    return json.dumps(
        {
            "name": manifest.get("name"),
            "current_layer": manifest.get("current_layer"),
            "current_descent": manifest.get("current_descent"),
            "layer_graph": layer_graph,
            "ascent_history": manifest.get("ascent_history", []),
            "pending_confirmations": manifest.get("pending_confirmations", []),
        },
        ensure_ascii=False,
        indent=2,
    )


# ── Baseline ────────────────────────────────────────────────

@mcp.tool()
def se_baseline(layer: str, reason: str = "") -> str:
    """Freeze specified layer as a baseline snapshot."""
    proj = _ensure_project()
    engine = WorkflowEngine(proj)
    result = engine.baseline(layer, reason)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def se_list_baselines(layer: str = "") -> str:
    """List baselines for a layer (or all layers if empty)."""
    proj = _ensure_project()
    layers_to_check = [layer] if layer else LAYERS
    result = {}
    for l in layers_to_check:
        result[l] = proj.list_baselines(l)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Ascend / Descend ────────────────────────────────────────

@mcp.tool()
def se_ascend(from_layer: str, to_layer: str, to_baseline: str, reason: str) -> str:
    """
    Ascend (rollback) from from_layer to to_layer's specified baseline.
    Triggers a new descent round; lower layers become superseded.
    """
    proj = _ensure_project()
    engine = WorkflowEngine(proj)
    try:
        result = engine.ascend(from_layer, to_layer, to_baseline, reason)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def se_descend(to_layer: str, reason: str = "") -> str:
    """Descend from current layer to a lower layer."""
    proj = _ensure_project()
    engine = WorkflowEngine(proj)
    try:
        result = engine.descend(to_layer, reason)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def se_can_descend() -> str:
    """Check if current layer can safely descend to next layer."""
    proj = _ensure_project()
    engine = WorkflowEngine(proj)
    ok, msg, next_layer = engine.can_descend_to_next()
    return json.dumps(
        {"can_descend": ok, "message": msg, "next_layer": next_layer},
        ensure_ascii=False,
    )


# ── Confirmations ───────────────────────────────────────────

@mcp.tool()
def se_require_confirmation(
    item_type: str, description: str, options: str = '["approve","reject","modify"]', blocking: bool = True
) -> str:
    """Create a blocking confirmation gate item."""
    proj = _ensure_project()
    engine = WorkflowEngine(proj)
    opts = json.loads(options)
    cfm_id = engine.require_confirmation(item_type, description, opts, blocking)
    return json.dumps({"confirmation_id": cfm_id, "status": "pending"}, ensure_ascii=False)


@mcp.tool()
def se_resolve_confirmation(confirmation_id: str, resolution: str, feedback: str = "") -> str:
    """Resolve a pending confirmation (approve/reject/modify)."""
    proj = _ensure_project()
    engine = WorkflowEngine(proj)
    try:
        result = engine.resolve_confirmation(confirmation_id, resolution, feedback)
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ── Document CRUD ───────────────────────────────────────────

@mcp.tool()
def se_store_document(layer: str, filename: str, content: str, doc_type: str = "generic") -> str:
    """Store/update a document in a layer directory."""
    proj = _ensure_project()
    path = proj.write_document(layer, filename, content, doc_type=doc_type)
    return json.dumps({"path": str(path), "status": "stored"}, ensure_ascii=False)


@mcp.tool()
def se_read_document(layer: str, filename: str) -> str:
    """Read a layer document (returns frontmatter + content)."""
    proj = _ensure_project()
    try:
        doc = proj.read_document(layer, filename)
        return json.dumps(doc, ensure_ascii=False, indent=2)
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def se_list_documents(layer: str = "") -> str:
    """List documents in a layer (or all layers)."""
    proj = _ensure_project()
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
    change_type: str, scope: str, reason: str, before: str = "", after: str = ""
) -> str:
    """Atomically log a change (must be called BEFORE actual modification)."""
    proj = _ensure_project()
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
def se_get_changelog(limit: int = 20) -> str:
    """Return recent changelog entries."""
    proj = _ensure_project()
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
) -> str:
    """
    Check document-code consistency.
    
    method="llm": Use LLM semantic audit (returns prompt for agent to call LLM)
    method="text": Local text-based existence check (no LLM required)
    method="ast": tree-sitter structured comparison (fallback to llm for now)
    """
    proj = _ensure_project()
    scope = json.loads(code_scope)

    if method == "llm" or method == "ast":
        auditor = LLMConsistencyAuditor(proj)
        result = auditor.audit(design_layer, design_doc, scope or None)
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif method == "text":
        checker = TextConsistencyChecker(proj)
        result = checker.check(design_layer, design_doc, scope or None)
        result["note"] = "Use method='llm' for full semantic audit with report storage"
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"error": f"Unknown method: {method}"}, ensure_ascii=False)


@mcp.tool()
def se_store_consistency_report(report_json: str) -> str:
    """Store a parsed LLM consistency report (call after getting LLM response)."""
    proj = _ensure_project()
    auditor = LLMConsistencyAuditor(proj)
    report_data = json.loads(report_json)
    report_path = auditor.store_report(report_data)
    return json.dumps(
        {"report_path": str(report_path), "status": "stored"},
        ensure_ascii=False,
    )


# ── Proposal search ─────────────────────────────────────────

@mcp.tool()
def se_search_proposals(
    query: str,
    scope: str = "local",
    method: str = "rg",
    archive_dir: str = "",
    top_k: int = 10,
) -> str:
    """
    Search for similar proposals across project documents.
    
    scope="local": Search within current project's layer docs
    scope="archive": Search in specified archive directory
    method="rg": ripgrep text search (default, zero cost)
    method="tfidf": TF-IDF cosine similarity (needs sklearn)
    """
    proj = _ensure_project()
    searcher = ProposalSearcher(proj)
    result = searcher.search(
        query=query,
        scope=scope,
        method=method,
        archive_dir=archive_dir or None,
        top_k=top_k,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Todo management ─────────────────────────────────────────

@mcp.tool()
def se_get_todos() -> str:
    """Get all todos across layers (excluding superseded layers)."""
    proj = _ensure_project()
    todos = proj.get_todos()
    return json.dumps(todos, ensure_ascii=False, indent=2)


@mcp.tool()
def se_update_todo(layer: str, todos_json: str) -> str:
    """Update todo list in a layer's README.md."""
    proj = _ensure_project()
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


# ── Project completion ──────────────────────────────────────


@mcp.tool()
def se_complete_project() -> str:
    """
    Mark the project as completed (L7 final acceptance closure).

    Prerequisites: current layer is L7-终验, L1-L6 all baselined, and no
    unresolved blocking confirmations. On success, L7 README is marked
    completed and the manifest records completed_at.
    """
    proj = _ensure_project()
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

    pending = manifest.get("pending_confirmations", [])
    unresolved = [
        p for p in pending if p.get("blocking", True) and not p.get("resolved_at")
    ]
    if unresolved:
        errors.append(
            f"{len(unresolved)} 个未解决的 blocking 门控: "
            f"{[p['id'] for p in unresolved]}"
        )

    if errors:
        return json.dumps(
            {"error": "完成前置条件未满足", "details": errors},
            ensure_ascii=False,
            indent=2,
        )

    engine = WorkflowEngine(proj)
    engine.mark_layer_completed("L7-终验")

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
        {"status": "completed", "completed_at": completed_at},
        ensure_ascii=False,
        indent=2,
    )


# ── Guidance ────────────────────────────────────────────────

@mcp.tool()
def se_get_next_steps() -> str:
    """Get recommended next actions based on current layer state."""
    proj = _ensure_project()
    manifest = proj.read_manifest()
    current = manifest.get("current_layer")
    descent = manifest.get("current_descent")
    pending = manifest.get("pending_confirmations", [])
    layer_states = manifest.get("layer_states", {})
    state = layer_states.get(current, {})

    unresolved = [p for p in pending if not p.get("resolved_at")]
    if unresolved:
        return json.dumps(
            {
                "current_layer": current,
                "descent": descent,
                "status": "awaiting_confirmation",
                "actions": [
                    f"Resolve confirmation {u['id']}: {u['description'][:50]}"
                    for u in unresolved
                ],
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
        },
        ensure_ascii=False,
        indent=2,
    )
