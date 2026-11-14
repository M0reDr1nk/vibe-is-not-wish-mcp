"""Tests for cross-language symbol extraction (L3 v0.10)."""

import shutil

import pytest

from vinw.store.project import Project
from vinw.workflow.consistency_llm import TextConsistencyChecker
from vinw.workflow.symbols import (
    DEFAULT_CODE_EXTENSIONS,
    extract_code_symbols,
    extract_design_identifiers,
    filter_symbols,
)


@pytest.fixture
def workdir(tmp_path):
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


class TestCodeExtraction:
    def test_c_functions_and_macros(self, workdir):
        src = workdir / "gemm.c"
        src.write_text(
            '#define MR 4\n'
            'static void pack_a(int mc) { }\n'
            'gemm_status gemm_f32(int M) { return GEMM_OK; }\n'
            'float only_declared(int x);\n'
        )
        symbols = extract_code_symbols(src)
        assert {"MR", "pack_a", "gemm_f32"} <= symbols
        # declarations belong to headers; a .c prototype is not an implementation
        assert "only_declared" not in symbols

    def test_header_declarations(self, workdir):
        hdr = workdir / "gemm.h"
        hdr.write_text(
            '#ifndef VINW_GEMM_H\n#define VINW_GEMM_H\n'
            'typedef enum { GEMM_OK = 0 } gemm_status;\n'
            'gemm_status gemm_f32(int M, int N, int K);\n'
            'int gemm_mr(void);\n'
            '#endif\n'
        )
        symbols = extract_code_symbols(hdr)
        assert "gemm_f32" in symbols
        assert "gemm_mr" in symbols

    def test_python_definitions(self, workdir):
        py = workdir / "mod.py"
        py.write_text("def alpha():\n    pass\n\nclass Beta:\n    pass\n")
        assert {"alpha", "Beta"} <= extract_code_symbols(py)

    def test_rust_and_go(self, workdir):
        rs = workdir / "lib.rs"
        rs.write_text("pub fn compute(a: i32) -> i32 { a }\nstruct Holder { x: i32 }\n")
        go = workdir / "main.go"
        go.write_text("package main\nfunc Run() int { return 0 }\ntype Thing struct{}\n")
        assert {"compute", "Holder"} <= extract_code_symbols(rs)
        assert {"Run", "Thing"} <= extract_code_symbols(go)


class TestFiltering:
    def test_keywords_dropped(self):
        assert filter_symbols({"enum", "struct", "int", "void", "def"}) == set()

    def test_header_guard_dropped(self):
        assert filter_symbols({"GEMM_H", "VINW_GEMM_H", "FOO_HPP"}) == set()

    def test_real_symbols_kept(self):
        assert filter_symbols({"gemm_f32", "pack_a", "MR"}) == {"gemm_f32", "pack_a", "MR"}

    def test_design_identifiers(self):
        content = "| `gemm_f32` | 入口 |\n调用 `pack_a` 与 macro_kernel(...)\n"
        ids = extract_design_identifiers(content)
        assert {"gemm_f32", "pack_a", "macro_kernel"} <= ids
        assert "enum" not in ids


class TestCheckerOnCProject:
    def _c_project(self, tmp_path):
        root = tmp_path / "cproj"
        proj = Project.init(root, "cproj", "C project")
        (root / "src").mkdir()
        (root / "src" / "gemm.c").write_text(
            "#include <stddef.h>\n"
            "void gemm_f32(int M) { }\n"
            "static void pack_a(int mc) { }\n"
        )
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "| 接口 |\n|------|\n| `gemm_f32` |\n| `pack_a` |\n",
        )
        return proj

    def test_c_project_passes(self, tmp_path):
        proj = self._c_project(tmp_path)
        result = TextConsistencyChecker(proj).check(code_scope=["src"])
        assert result["overall"] == "passed", result
        assert result["files_scanned"] == 1
        assert ".c" in result["extensions"]

    def test_keywords_do_not_create_noise(self, tmp_path):
        proj = self._c_project(tmp_path)
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "typedef enum { X } gemm_status;\n| `gemm_f32` |\n",
        )
        result = TextConsistencyChecker(proj).check(code_scope=["src"])
        descriptions = " ".join(i["description"] for i in result["inconsistencies"])
        assert "'enum'" not in descriptions
        assert "'gemm_status'" not in descriptions

    def test_missing_symbol_still_detected(self, tmp_path):
        proj = self._c_project(tmp_path)
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "| `gemm_f32` |\n| `gemm_never_written` |\n",
        )
        result = TextConsistencyChecker(proj).check(code_scope=["src"])
        assert any("gemm_never_written" in i["description"] for i in result["inconsistencies"])

    def test_code_extensions_configurable(self, tmp_path):
        proj = self._c_project(tmp_path)
        manifest = proj.read_manifest()
        manifest["code_extensions"] = [".py"]  # C files no longer scanned
        proj.write_manifest(manifest)

        result = TextConsistencyChecker(proj).check(code_scope=["src"])
        assert "error" in result
        assert result["extensions"] == [".py"]


class TestRegexRobustness:
    """Regression: greedy matching must not swallow symbols across lines."""

    def test_preprocessor_block_does_not_swallow_function(self, workdir):
        src = workdir / "mod.c"
        src.write_text(
            "#if defined(USE_OPENMP) && defined(_OPENMP)\n"
            "#include <omp.h>\n"
            "#define HAS_OMP 1\n"
            "#else\n"
            "#define HAS_OMP 0\n"
            "#endif\n"
            "\n"
            "const char *impl_name(void) { return \"x\"; }\n"
            "int impl_id(void) { return 1; }\n"
        )
        symbols = extract_code_symbols(src)
        assert "impl_name" in symbols, "preprocessor block swallowed the function"
        assert "impl_id" in symbols

    def test_preprocessor_words_filtered(self, workdir):
        src = workdir / "m.c"
        # note: single-character names are dropped by design (len < 2)
        src.write_text("#if defined(_OPENMP)\nint func_ok(void) { return 0; }\n#endif\n")
        symbols = extract_code_symbols(src)
        assert "func_ok" in symbols
        assert not ({"defined", "if", "endif"} & symbols)
        assert "_OPENMP" not in symbols


class TestRequiredVsAdvisory:
    """Only API-surface mentions block; config keys/enum values are advisory."""

    def test_api_table_rows_are_required(self):
        from vinw.workflow.symbols import split_design_symbols

        content = "| 工具 | 输入 |\n|------|------|\n| `se_foo` | x |\n"
        required, advisory = split_design_symbols(content)
        assert "se_foo" in required

    def test_config_table_rows_are_advisory(self):
        from vinw.workflow.symbols import split_design_symbols

        content = "| 字段 | 类型 |\n|------|------|\n| `consistency_policy` | str |\n"
        required, advisory = split_design_symbols(content)
        assert "consistency_policy" not in required
        assert "consistency_policy" in advisory

    def test_json_block_does_not_create_required(self):
        from vinw.workflow.symbols import split_design_symbols

        content = '```json\n{"overall": "passed", "gaps": []}\n```\n'
        required, _ = split_design_symbols(content)
        assert required == set()

    def test_fenced_python_signature_is_required(self):
        from vinw.workflow.symbols import split_design_symbols

        content = "```python\ndef compute_gemm(M, N):\n    pass\n```\n"
        required, _ = split_design_symbols(content)
        assert "compute_gemm" in required

    def test_sql_block_does_not_create_required(self):
        from vinw.workflow.symbols import split_design_symbols

        content = "```sql\nCREATE TABLE t (state TEXT CHECK (state IN ('a','b')));\n```\n"
        required, _ = split_design_symbols(content)
        assert required == set()

    def test_advisory_missing_is_reported_but_not_blocking(self, tmp_path):
        from vinw.store.project import Project
        from vinw.workflow.consistency_llm import TextConsistencyChecker

        root = tmp_path / "adv"
        proj = Project.init(root, "adv", "")
        (root / "main.py").write_text("def present():\n    pass\n")
        proj.write_document(
            "L3-方案细化",
            "api-design.md",
            "| 接口 |\n|------|\n| `present` |\n\n| 字段 | 说明 |\n|------|------|\n| `some_key` | x |\n",
        )
        result = TextConsistencyChecker(proj).check(code_scope=["main.py"])
        assert result["overall"] == "passed"
        assert "some_key" in result["advisory_missing"]
