"""Adopt-existing-codebase mode (v0.23, R36-R40).

Guards, happy path, next_steps guidance, and the compatibility red line:
default (adopt_existing=False) behaviour must stay byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vinw.store.project import AdoptError, LAYERS, Project


def _make_repo(tmp_path: Path) -> Path:
    """A minimal existing code repository."""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (repo / "README.md").write_text("# existing\n", encoding="utf-8")
    return repo


# ── Happy path ──────────────────────────────────────────────


def test_adopt_non_empty_repo(tmp_path):
    repo = _make_repo(tmp_path)
    proj = Project.adopt(repo, "legacy", "既有系统改造")

    assert proj.root == repo.resolve()
    assert (repo / ".vinw" / "manifest.md").exists()
    for layer in LAYERS:
        assert (repo / layer / "README.md").exists()

    manifest = proj.read_manifest()
    assert manifest["work_mode"] == "existing-codebase"
    assert manifest["code_root"] == "."
    assert manifest["adopted_at"]
    assert manifest["current_layer"] == "L1-需求拆解"

    # Existing code untouched
    assert (repo / "src" / "app.py").read_text(encoding="utf-8").startswith("def main")


def test_adopt_seeds_l1_todo_checklist(tmp_path):
    repo = _make_repo(tmp_path)
    proj = Project.adopt(repo, "legacy")

    content = proj.read_layer_readme("L1-需求拆解")["content"]
    assert "现状摸底" in content
    assert "legacy-debt" in content
    # Template placeholder replaced (baseline guard would pass once checked)
    assert "- [ ] 初始化本层工作" not in content


def test_adopt_writes_changelog_entry(tmp_path):
    repo = _make_repo(tmp_path)
    proj = Project.adopt(repo, "legacy")

    changelog = (repo / ".vinw" / "changelog.md").read_text(encoding="utf-8")
    assert "`adopt`" in changelog
    assert "existing-codebase" in changelog


def test_adopt_reuses_empty_layer_named_dir(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "L7-终验").mkdir()  # empty pre-existing dir named like a layer
    proj = Project.adopt(repo, "legacy")
    assert (repo / "L7-终验" / "README.md").exists()
    assert proj.read_manifest()["work_mode"] == "existing-codebase"


# ── Guards ──────────────────────────────────────────────────


def test_adopt_refuses_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        Project.adopt(tmp_path / "nope", "x")


def test_adopt_refuses_file_root(tmp_path):
    """GAP-002: a file (not a directory) as root raises NotADirectoryError."""
    a_file = tmp_path / "file.txt"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        Project.adopt(a_file, "x")


def test_adopt_refuses_partial_vinw_dir(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / ".vinw").mkdir()
    with pytest.raises(AdoptError, match="半初始化"):
        Project.adopt(repo, "x")
    # Nothing else created
    assert not (repo / "L1-需求拆解").exists()


def test_adopt_refuses_non_empty_layer_conflict(tmp_path):
    repo = _make_repo(tmp_path)
    conflict = repo / "L4-编码实现"
    conflict.mkdir()
    (conflict / "code.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(AdoptError) as ei:
        Project.adopt(repo, "x")
    assert "L4-编码实现" in str(ei.value)
    assert ei.value.conflicts == ["L4-编码实现"]
    assert not (repo / ".vinw").exists()


# ── MCP surface ─────────────────────────────────────────────


def test_se_init_project_adopt_existing(tmp_path, monkeypatch):
    import vinw.server as server

    monkeypatch.setattr(server, "_active_project", None)
    repo = _make_repo(tmp_path)
    out = json.loads(
        server.se_init_project("legacy", str(repo), "改造", adopt_existing=True)
    )
    assert out["adopted_existing"] is True
    assert out["work_mode"] == "existing-codebase"
    assert out["code_root"] == "."
    assert out["current_layer"] == "L1-需求拆解"
    assert server._active_project.root == repo.resolve()


def test_se_init_project_adopt_guard_structured_error(tmp_path, monkeypatch):
    import vinw.server as server

    monkeypatch.setattr(server, "_active_project", None)
    repo = _make_repo(tmp_path)
    (repo / ".vinw").mkdir()
    out = json.loads(
        server.se_init_project("legacy", str(repo), adopt_existing=True)
    )
    assert "error" in out
    assert "半初始化" in out["error"]
    assert "vinw-design" in out["hint"]


def test_se_init_project_default_unchanged(tmp_path, monkeypatch):
    """Compatibility red line: default path still appends name and needs empty dir."""
    import vinw.server as server

    monkeypatch.setattr(server, "_active_project", None)
    parent = tmp_path / "parent"
    parent.mkdir()
    out = json.loads(server.se_init_project("green", str(parent)))
    assert out["project_id"] == str(parent / "green")
    assert "adopted_existing" not in out
    assert (parent / "green" / ".vinw" / "manifest.md").exists()


def test_se_init_project_adopt_idempotent(tmp_path, monkeypatch):
    """GAP-001: re-adopting an existing project returns adopted without
    the adopted_existing marker."""
    import vinw.server as server

    monkeypatch.setattr(server, "_active_project", None)
    repo = _make_repo(tmp_path)
    Project.adopt(repo, "legacy")

    out = json.loads(
        server.se_init_project("legacy", str(repo), adopt_existing=True)
    )
    assert out["adopted"] is True
    assert "adopted_existing" not in out
    assert out["current_layer"] == "L1-需求拆解"


def test_next_steps_existing_codebase_guidance(tmp_path, monkeypatch):
    import vinw.server as server

    repo = _make_repo(tmp_path)
    proj = Project.adopt(repo, "legacy")
    monkeypatch.setattr(server, "_active_project", proj)

    out = json.loads(server.se_get_next_steps())
    assert out["current_layer"] == "L1-需求拆解"
    joined = " ".join(out["suggested_work"])
    assert "现状摸底" in joined
    assert "legacy-debt" in joined
    assert "existing-codebase" in out["special_instruction"]
    # INC-001 fix: gate carries the survey-confirmation suffix
    assert "摸底" in (out["gate_before_leave"] or "")


def test_next_steps_greenfield_unchanged(tmp_path, monkeypatch):
    import vinw.server as server

    proj = Project.init(tmp_path / "green", "green")
    monkeypatch.setattr(server, "_active_project", proj)

    out = json.loads(server.se_get_next_steps())
    assert out["suggested_work"] == [
        "Decompose requirements → proposals.md",
        "Identify key problem domains",
    ]
    assert "existing-codebase" not in out["special_instruction"]


def test_next_steps_existing_codebase_l4_guidance(tmp_path, monkeypatch):
    """GAP-003: the L4 branch steers in-place modification (INC-002 decided:
    replace semantics + all-layer special_instruction are the design)."""
    import frontmatter

    import vinw.server as server
    from vinw.store.project import replace_todo_section
    from vinw.workflow.state_machine import WorkflowEngine

    repo = _make_repo(tmp_path)
    proj = Project.adopt(repo, "legacy")
    monkeypatch.setattr(server, "_active_project", proj)

    def clear_todo(layer: str) -> None:
        path = proj.get_layer_dir(layer) / "README.md"
        post = frontmatter.load(path)
        post.content = replace_todo_section(
            post.content, "## 当前待办\n\n- [x] 准备\n"
        )
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    engine = WorkflowEngine(proj)
    clear_todo("L1-需求拆解")
    engine.baseline("L1-需求拆解")
    engine.descend("L2-参考文献与方案搜证汇总")
    clear_todo("L2-参考文献与方案搜证汇总")
    engine.baseline("L2-参考文献与方案搜证汇总")
    engine.descend("L3-方案细化")
    clear_todo("L3-方案细化")
    engine.baseline("L3-方案细化")
    engine.descend("L4-编码实现")

    out = json.loads(server.se_get_next_steps())
    assert out["current_layer"] == "L4-编码实现"
    joined = " ".join(out["suggested_work"])
    assert "Modify existing code in place" in joined
    assert "existing-codebase" in out["special_instruction"]


# ── INC-004 fix: CLI idempotent adopt ───────────────────────


def test_cli_adopt_idempotent(tmp_path, capsys, monkeypatch):
    """Re-running `vinw init --adopt-existing` on a VINW project exits 0."""
    import sys

    from vinw.__main__ import main

    repo = _make_repo(tmp_path)
    Project.adopt(repo, "legacy")

    monkeypatch.setattr(
        sys, "argv", ["vinw", "init", str(repo), "--name", "legacy", "--adopt-existing"]
    )
    with pytest.raises(SystemExit) as ei:
        main()
    assert ei.value.code == 0
    assert "Already a VINW project" in capsys.readouterr().out


def test_cli_adopt_success_output(tmp_path, capsys, monkeypatch):
    """GAP-004: CLI adopt prints the sanctioned output contract."""
    import sys

    from vinw.__main__ import main

    repo = _make_repo(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["vinw", "init", str(repo), "--name", "legacy", "--adopt-existing", "--no-register"],
    )
    main()  # success path returns normally
    out = capsys.readouterr().out
    assert "Adopted existing repo" in out
    assert "existing-codebase" in out
    assert (repo / ".vinw" / "manifest.md").exists()


def test_cli_adopt_guard_exit_code(tmp_path, capsys, monkeypatch):
    """GAP-004: a refused adopt exits non-zero with the error on stdout."""
    import sys

    from vinw.__main__ import main

    repo = _make_repo(tmp_path)
    (repo / ".vinw").mkdir()
    monkeypatch.setattr(
        sys, "argv", ["vinw", "init", str(repo), "--name", "legacy", "--adopt-existing"]
    )
    with pytest.raises(SystemExit) as ei:
        main()
    assert ei.value.code == 1
    assert "半初始化" in capsys.readouterr().out
