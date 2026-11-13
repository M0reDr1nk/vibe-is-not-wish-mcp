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
    def test_no_symbols_returns_passed(self, proj):
        checker = TextConsistencyChecker(proj)
        result = checker.check()
        # Design doc with no extractable symbols and no code -> passed (nothing to check)
        assert result["overall"] == "passed"

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
        checker = TextConsistencyChecker(proj)
        result = checker.check()
        assert result["overall"] == "warning"
        assert len(result["inconsistencies"]) >= 1
        assert "missing_func" in result["inconsistencies"][0]["description"]

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
