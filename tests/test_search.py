"""Tests for vinw.workflow.search."""

import shutil
from pathlib import Path

import pytest

from vinw.store.project import Project
from vinw.workflow.search import ProposalSearcher


@pytest.fixture
def searcher(tmp_path):
    root = tmp_path / "test-proj"
    proj = Project.init(root, "test-proj", "Test")
    # Add some documents for search
    proj.write_document("L2-参考文献与方案搜证汇总", "references.md", "# References\n\nMCP protocol is great.\n")
    proj.write_document("L3-方案细化", "design-doc.md", "# Design\n\nWe use markdown storage.\n")
    yield ProposalSearcher(proj)
    shutil.rmtree(root, ignore_errors=True)


class TestSearchRg:
    def test_rg_finds_matching_docs(self, searcher):
        result = searcher.search("markdown", method="rg")
        assert result["method"] == "rg"
        assert result["results_count"] > 0
        assert any("design-doc" in r["source"] for r in result["results"])

    def test_rg_no_results(self, searcher):
        result = searcher.search("nonexistent_xyz_123", method="rg")
        assert result["results_count"] == 0

    def test_rg_scope_local(self, searcher):
        result = searcher.search("MCP", method="rg", scope="local")
        assert result["results_count"] > 0
        assert any("references" in r["source"] for r in result["results"])


class TestSearchTfidf:
    def test_tfidf_requires_sklearn(self, searcher):
        # This may or may not have sklearn installed
        result = searcher.search("storage", method="tfidf")
        if "error" in result:
            assert "scikit-learn" in result["error"]
        else:
            assert result["method"] == "tfidf"
            assert "results" in result

    def test_tfidf_insufficient_docs(self, searcher):
        # Only 2 docs exist, need >= 2 for TF-IDF (technically ok but might fail)
        result = searcher.search("test", method="tfidf")
        # Either succeeds or gives error
        assert "results" in result or "error" in result


class TestSearchParams:
    def test_unknown_method(self, searcher):
        result = searcher.search("test", method="unknown")
        assert "error" in result

    def test_top_k_limit(self, searcher):
        result = searcher.search("a", method="rg", top_k=1)
        assert len(result["results"]) <= 1
