"""Proposal search — ripgrep + TF-IDF hybrid."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..store.project import Project, LAYERS


@dataclass
class SearchResult:
    source: str          # file path or layer name
    relevance: float     # 0-1 score
    excerpt: str         # matching excerpt
    context: str         # surrounding context


class ProposalSearcher:
    """Search for similar proposals across project archives."""

    def __init__(self, project: Project):
        self.project = project

    def search(
        self,
        query: str,
        scope: str = "local",       # "local" | "archive"
        method: str = "rg",         # "rg" | "tfidf"
        archive_dir: str | None = None,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """
        Search for proposals matching query.
        
        method="rg": Use ripgrep for fast text search (default, zero cost)
        method="tfidf": Use TF-IDF when archive > 50 docs or rg quality poor
        """
        if method == "rg":
            return self._search_rg(query, scope, archive_dir, top_k)
        elif method == "tfidf":
            return self._search_tfidf(query, scope, archive_dir, top_k)
        else:
            return {"error": f"Unknown method: {method}"}

    def _search_rg(
        self,
        query: str,
        scope: str,
        archive_dir: str | None,
        top_k: int,
    ) -> dict[str, Any]:
        """Search using ripgrep."""
        if scope == "local":
            # Search within current project's layer docs
            search_roots = [self.project.root / layer for layer in LAYERS]
        elif scope == "archive" and archive_dir:
            search_roots = [Path(archive_dir)]
        else:
            return {"error": "archive_dir required for scope='archive'"}

        results: list[SearchResult] = []
        keywords = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]

        for root in search_roots:
            if not root.exists():
                continue
            for md_file in root.rglob("*.md"):
                if ".baseline" in str(md_file):
                    continue
                content = md_file.read_text(encoding="utf-8")
                content_lower = content.lower()

                score = 0
                excerpts = []
                for kw in keywords:
                    count = content_lower.count(kw)
                    if count > 0:
                        score += count
                        # Find context around first occurrence
                        idx = content_lower.find(kw)
                        start = max(0, idx - 100)
                        end = min(len(content), idx + 200)
                        excerpt = content[start:end].replace("\n", " ")
                        if excerpt not in [e.excerpt for e in results]:
                            excerpts.append(excerpt)

                if score > 0:
                    # Normalize by doc length
                    normalized_score = min(1.0, score / (len(content) / 1000 + 1))
                    results.append(
                        SearchResult(
                            source=str(md_file.relative_to(self.project.root if scope == "local" else root)),
                            relevance=round(normalized_score, 3),
                            excerpt=excerpts[0] if excerpts else "",
                            context=content[:500],
                        )
                    )

        results.sort(key=lambda r: r.relevance, reverse=True)
        return {
            "method": "rg",
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "source": r.source,
                    "relevance": r.relevance,
                    "excerpt": r.excerpt[:300],
                }
                for r in results[:top_k]
            ],
        }

    def _search_tfidf(
        self,
        query: str,
        scope: str,
        archive_dir: str | None,
        top_k: int,
    ) -> dict[str, Any]:
        """Search using TF-IDF cosine similarity."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            return {
                "error": "scikit-learn not installed. Run: pip install scikit-learn",
                "fallback": "Use method='rg' instead",
            }

        if scope == "local":
            docs_dir = self.project.root
        elif scope == "archive" and archive_dir:
            docs_dir = Path(archive_dir)
        else:
            return {"error": "archive_dir required for scope='archive'"}

        # Collect all markdown documents
        documents: list[str] = []
        doc_paths: list[str] = []

        for md_file in docs_dir.rglob("*.md"):
            if ".baseline" in str(md_file) or md_file.name == "README.md":
                continue
            content = md_file.read_text(encoding="utf-8")
            # Strip frontmatter for TF-IDF
            if content.startswith("---"):
                parts = content.split("---", 2)
                content = parts[2] if len(parts) >= 3 else content
            documents.append(content)
            doc_paths.append(str(md_file.relative_to(docs_dir)))

        if len(documents) < 2:
            return {
                "error": f"Only {len(documents)} documents found. Need >= 2 for TF-IDF.",
                "fallback": "Use method='rg' instead",
            }

        # Fit TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
        )
        doc_matrix = vectorizer.fit_transform(documents)
        query_vec = vectorizer.transform([query])

        similarities = cosine_similarity(query_vec, doc_matrix).flatten()
        ranked_indices = similarities.argsort()[::-1]

        results = []
        for idx in ranked_indices[:top_k]:
            if similarities[idx] <= 0:
                break
            results.append(
                {
                    "source": doc_paths[idx],
                    "relevance": round(float(similarities[idx]), 3),
                    "excerpt": documents[idx][:300].replace("\n", " "),
                }
            )

        return {
            "method": "tfidf",
            "query": query,
            "documents_indexed": len(documents),
            "results_count": len(results),
            "results": results,
        }
