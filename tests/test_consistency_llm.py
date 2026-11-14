"""Tests for vinw.workflow.consistency_llm."""

import shutil
from pathlib import Path

import pytest

from vinw.store.project import Project
from vinw.workflow.consistency_llm import TextConsistencyChecker, LLMConsistencyAuditor


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "test-proj"
    p = Project.init(root, "test-proj", "Test")
    yield p
    shutil.rmtree(root, ignore_errors=True)


class TestTextConsistencyChecker:
    def test_empty_scan_is_an_error_not_a_pass(self, proj):
        """No code files is a configuration problem (L3 v0.10 / R13)."""
        checker = TextConsistencyChecker(proj)
        result = checker.check()
        assert "error" in result
        assert result["extensions"]

    def test_symbol_extraction(self, proj):
        proj.write_document("L3-方案细化", "api-design.md", """
| 接口名 | 方法 |
|--------|------|
| `se_init_project` | init |
| `se_get_project` | get |
""")
        checker = TextConsistencyChecker(proj)
        symbols = checker._extract_symbols(proj.read_document("L3-方案细化", "api-design.md")["content"])
        names = [s["name"] for s in symbols]
        assert "se_init_project" in names
        assert "se_get_project" in names

    def test_symbol_match_found(self, proj):
        # Write design with a function
        proj.write_document("L3-方案细化", "api-design.md", """
```python
def hello_world():
    pass
```
""")
        # Write code with same function
        src_dir = proj.root / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def hello_world():\n    return 'hello'\n")

        checker = TextConsistencyChecker(proj)
        result = checker.check(code_scope=["src"])
        assert result["overall"] == "passed"
        assert len(result["matched"]) == 1

    def test_symbol_missing_reported(self, proj):
        proj.write_document("L3-方案细化", "api-design.md", """
```python
def missing_func():
    pass
```
""")
        # Need at least one code file so the scan is not empty
        src = proj.root / "src"
        src.mkdir(exist_ok=True)
        (src / "other.py").write_text("def present_func():\n    pass\n")

        checker = TextConsistencyChecker(proj)
        result = checker.check(code_scope=["src"])
        assert result["overall"] == "warning"
        assert any("missing_func" in i["description"] for i in result["inconsistencies"])

    def test_header_not_extracted(self, proj):
        """Ensure table headers like 'layer' are not extracted as symbols."""
        proj.write_document("L3-方案细化", "api-design.md", """
| layer | name |
|-------|------|
| L1    | test |
""")
        checker = TextConsistencyChecker(proj)
        symbols = checker._extract_symbols(proj.read_document("L3-方案细化", "api-design.md")["content"])
        names = [s["name"] for s in symbols]
        assert "layer" not in names

    def test_code_root_from_manifest(self, proj):
        """manifest code_root points to the code repo (self-hosting layout)."""
        repo = proj.root.parent  # code_root ".." resolves here
        pkg = repo / "vinw"
        pkg.mkdir(exist_ok=True)
        (pkg / "server.py").write_text("def se_hello_tool():\n    pass\n")
        proj.write_document("L3-方案细化", "api-design.md", """
| 接口名 |
|--------|
| `se_hello_tool` |
""")
        manifest = proj.read_manifest()
        manifest["code_root"] = ".."
        proj.write_manifest(manifest)

        checker = TextConsistencyChecker(proj)
        result = checker.check(code_scope=["vinw"])
        assert result["overall"] == "passed"
        assert any(m["symbol"] == "se_hello_tool" for m in result["matched"])

    def test_code_scope_supports_file_entry(self, proj):
        """code_scope entries may be files, not only directories."""
        proj.write_document("L3-方案细化", "api-design.md", """
| 接口名 |
|--------|
| `se_file_tool` |
""")
        (proj.root / "main.py").write_text("def se_file_tool():\n    pass\n")

        checker = TextConsistencyChecker(proj)
        result = checker.check(code_scope=["main.py"])
        assert result["overall"] == "passed"
        assert len(result["matched"]) == 1


class TestLLMConsistencyAuditor:
    def test_audit_prepares_prompt(self, proj):
        proj.write_document("L3-方案细化", "api-design.md", "# Design\n\ndef test(): pass")
        # Create a code file so audit can find code
        (proj.root / "main.py").write_text("# code\n")
        auditor = LLMConsistencyAuditor(proj)
        result = auditor.audit()
        assert result["status"] == "prompt_ready"
        assert "prompt" in result
        assert "test" in result["prompt"]

    def test_audit_missing_design_error(self, proj):
        auditor = LLMConsistencyAuditor(proj)
        result = auditor.audit(design_doc="nonexistent.md")
        assert "error" in result

    def test_store_report(self, proj):
        auditor = LLMConsistencyAuditor(proj)
        report_data = {
            "overall": "passed",
            "inconsistencies": [],
            "matched": [{"design_ref": "a", "code_ref": "b", "symbol": "c", "note": "ok"}],
        }
        path = auditor.store_report(report_data, report_id="test-001")
        assert path.exists()
        assert "report-test-001" in str(path)
        content = path.read_text()
        assert "passed" in content


class TestGateErrorHints:
    """L3 v0.10 / R14: hints must match the actual failure reason."""

    def test_consistency_failure_hint_is_not_about_todos(self, proj, monkeypatch):
        import json

        import vinw.server as server

        saved = server._active_project
        server._active_project = proj
        try:
            readme = proj.read_layer_readme("L4-编码实现")
            proj.write_layer_readme(
                "L4-编码实现",
                readme,
                readme["content"].replace("- [ ] 初始化本层工作", "- [x] 实现完成"),
            )
            (proj.root / "main.py").write_text("def main():\n    return 0\n")
            # two rows: first is the header, second declares the symbol
            proj.write_document(
                "L3-方案细化",
                "api-design.md",
                "| 接口名 |\n|--------|\n| `se_not_implemented` |\n",
            )
            result = json.loads(server.se_baseline("L4-编码实现"))
            assert "error" in result
            assert "todo" not in result["hint"].lower()
            assert "consistency-reports" in result["hint"]
            assert result["consistency"] is not None
        finally:
            server._active_project = saved

    def test_placeholder_failure_hint_mentions_todos(self, proj, monkeypatch):
        import json

        import vinw.server as server

        saved = server._active_project
        server._active_project = proj
        try:
            result = json.loads(server.se_baseline("L1-需求拆解"))
            assert "error" in result
            assert "se_update_todo" in result["hint"]
        finally:
            server._active_project = saved
