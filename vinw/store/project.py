"""Project storage layer — Markdown-first, spiral-ascend architecture."""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from ..utils.templates import (
    MANIFEST_TEMPLATE_V2,
    LAYER_README_TEMPLATE,
    REFERENCES_TEMPLATE,
    EVIDENCE_MATRIX_TEMPLATE,
    SYNTHESIS_TEMPLATE,
    DESIGN_DOC_TEMPLATE,
    API_DESIGN_TEMPLATE,
    IMPLEMENTATION_TEMPLATE,
    TEST_PLAN_TEMPLATE,
    TEST_RESULTS_TEMPLATE,
    DEBUG_SESSION_TEMPLATE,
    CLEANUP_LOG_TEMPLATE,
    FINAL_REPORT_TEMPLATE,
    ASCENSION_ENTRY_TEMPLATE,
)

LAYERS: list[str] = [
    "L1-需求拆解",
    "L2-参考文献与方案搜证汇总",
    "L3-方案细化",
    "L4-编码实现",
    "L5-测试验证",
    "L6-检视清理",
    "L7-终验",
]

LAYER_TEMPLATES: dict[str, dict[str, str]] = {
    "L1-需求拆解": {
        "README.md": LAYER_README_TEMPLATE,
        "proposals.md": "---\nse_version: \"2.0\"\nlayer: \"L1-需求拆解\"\ndoc_type: \"proposals\"\n---\n\n# 需求拆解\n\n## 原始需求\n\n## 分解结果\n\n| 编号 | 子需求 | 优先级 | 约束 |\n|------|--------|--------|------|\n| — | — | — | — |\n",
    },
    "L2-参考文献与方案搜证汇总": {
        "README.md": LAYER_README_TEMPLATE,
        "references.md": REFERENCES_TEMPLATE,
        "evidence-matrix.md": EVIDENCE_MATRIX_TEMPLATE,
        "synthesis.md": SYNTHESIS_TEMPLATE,
    },
    "L3-方案细化": {
        "README.md": LAYER_README_TEMPLATE,
        "design-doc.md": DESIGN_DOC_TEMPLATE,
        "api-design.md": API_DESIGN_TEMPLATE,
        "checkpoints.md": "---\nse_version: \"2.0\"\nlayer: \"L3-方案细化\"\ndoc_type: \"checkpoints\"\n---\n\n# 设计约束与检查点\n\n- [ ] 架构决策已记录\n- [ ] 接口签名已冻结\n- [ ] 数据模型已确认\n",
    },
    "L4-编码实现": {
        "README.md": LAYER_README_TEMPLATE,
        "implementation.md": IMPLEMENTATION_TEMPLATE,
        "code-map.md": "---\nse_version: \"2.0\"\nlayer: \"L4-编码实现\"\ndoc_type: \"code-map\"\n---\n\n# 代码-设计映射表\n\n| 设计文档 | 段落 | 代码文件 | 函数/类 | 状态 |\n|---------|------|---------|--------|------|\n| — | — | — | — | — |\n",
        "consistency-reports": "dir",
    },
    "L5-测试验证": {
        "README.md": LAYER_README_TEMPLATE,
        "test-plan.md": TEST_PLAN_TEMPLATE,
        "test-results.md": TEST_RESULTS_TEMPLATE,
        "iterations.md": "---\nse_version: \"2.0\"\nlayer: \"L5-测试验证\"\ndoc_type: \"iterations\"\n---\n\n# 测试-修复迭代记录\n\n| 轮次 | 测试结果 | 发现问题 | 修复方案 | 再测试结果 |\n|------|---------|---------|---------|-----------|\n| — | — | — | — | — |\n",
        "debug-sessions": "dir",
    },
    "L6-检视清理": {
        "README.md": LAYER_README_TEMPLATE,
        "cleanup-log.md": CLEANUP_LOG_TEMPLATE,
    },
    "L7-终验": {
        "README.md": LAYER_README_TEMPLATE,
        "final-report.md": FINAL_REPORT_TEMPLATE,
    },
}


class Project:
    """Markdown-first project store with baseline freeze/rollback support."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.vinw_dir = self.root / ".vinw"
        self.manifest_path = self.vinw_dir / "manifest.md"

    @classmethod
    def init(cls, root: Path, name: str, description: str = "") -> "Project":
        root = Path(root)
        if root.exists() and any(root.iterdir()):
            raise FileExistsError(f"Directory not empty: {root}")
        root.mkdir(parents=True, exist_ok=True)

        vinw_dir = root / ".vinw"
        vinw_dir.mkdir()

        # manifest.md
        manifest_post = frontmatter.loads(
            MANIFEST_TEMPLATE_V2.format(
                name=name,
                description=description,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        manifest_meta = manifest_post.metadata
        manifest = frontmatter.Post(content="", **manifest_meta)
        (vinw_dir / "manifest.md").write_text(
            frontmatter.dumps(manifest), encoding="utf-8"
        )

        # changelog.md
        (vinw_dir / "changelog.md").write_text(
            f'---\nse_version: "2.0"\nproject: "{name}"\n---\n\n# 变更日志\n',
            encoding="utf-8",
        )

        # ascensions.md
        ascensions = frontmatter.Post(
            content="# 上升回溯记录\n\n<!-- 每次上升操作追加记录 -->\n",
            **{"se_version": "2.0", "project": name, "doc_type": "ascensions"},
        )
        (vinw_dir / "ascensions.md").write_text(
            frontmatter.dumps(ascensions), encoding="utf-8"
        )

        # decisions.md
        (vinw_dir / "decisions.md").write_text(
            f'---\nse_version: "2.0"\nproject: "{name}"\ndoc_type: "decisions"\n---\n\n# 决策记录\n',
            encoding="utf-8",
        )

        # Layer directories + templates
        for layer in LAYERS:
            layer_dir = root / layer
            layer_dir.mkdir()
            baseline_dir = layer_dir / ".baseline"
            baseline_dir.mkdir()

            templates = LAYER_TEMPLATES.get(layer, {})
            for filename, tmpl in templates.items():
                if tmpl == "dir":
                    (layer_dir / filename).mkdir()
                    continue
                if callable(tmpl):
                    content = tmpl.format(layer=layer)
                else:
                    content = tmpl.format(layer=layer, updated_at=datetime.now(timezone.utc).isoformat())
                (layer_dir / filename).write_text(content, encoding="utf-8")

            # Ensure README.md exists
            readme_path = layer_dir / "README.md"
            if not readme_path.exists():
                readme = frontmatter.Post(
                    content=LAYER_README_TEMPLATE.format(layer=layer),
                    **{
                        "se_version": "2.0",
                        "layer": layer,
                        "doc_type": "layer-readme",
                        "status": "pending",
                        "descent_count": 0,
                    },
                )
                readme_path.write_text(frontmatter.dumps(readme), encoding="utf-8")

        return cls(root)

    # ── Manifest ──────────────────────────────────────────────

    def read_manifest(self) -> dict[str, Any]:
        post = frontmatter.load(self.manifest_path)
        return {**post.metadata, "content": post.content}

    def write_manifest(self, metadata: dict[str, Any], content: str = "") -> None:
        meta = {k: v for k, v in metadata.items() if k != "content"}
        post = frontmatter.Post(content=content or metadata.get("content", ""), **meta)
        self.manifest_path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def get_current_layer(self) -> str:
        return self.read_manifest().get("current_layer", LAYERS[0])

    # ── Paths ─────────────────────────────────────────────────

    def get_layer_dir(self, layer: str) -> Path:
        return self.root / layer

    def get_baseline_dir(self, layer: str) -> Path:
        return self.get_layer_dir(layer) / ".baseline"

    # ── Layer README helpers ──────────────────────────────────

    def read_layer_readme(self, layer: str) -> dict[str, Any]:
        path = self.get_layer_dir(layer) / "README.md"
        if not path.exists():
            return {}
        post = frontmatter.load(path)
        return {**post.metadata, "content": post.content}

    def write_layer_readme(self, layer: str, metadata: dict[str, Any], content: str) -> None:
        path = self.get_layer_dir(layer) / "README.md"
        meta = {k: v for k, v in metadata.items() if k != "content"}
        post = frontmatter.Post(content=content, **meta)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ── Baseline operations ───────────────────────────────────

    def list_baselines(self, layer: str) -> list[str]:
        bdir = self.get_baseline_dir(layer)
        if not bdir.exists():
            return []
        return sorted([p.stem for p in bdir.glob("*.md")])

    def read_baseline(self, layer: str, version: str) -> dict[str, Any]:
        path = self.get_baseline_dir(layer) / f"{version}.md"
        if not path.exists():
            raise FileNotFoundError(f"Baseline not found: {layer}/{version}")
        post = frontmatter.load(path)
        return {**post.metadata, "content": post.content}

    def freeze_baseline(self, layer: str, version: str, reason: str = "") -> Path:
        """Freeze current README.md as a baseline snapshot."""
        bdir = self.get_baseline_dir(layer)
        bdir.mkdir(parents=True, exist_ok=True)

        src = self.get_layer_dir(layer) / "README.md"
        dst = bdir / f"{version}.md"

        if not src.exists():
            raise FileNotFoundError(f"{layer}/README.md missing, cannot baseline")

        post = frontmatter.load(src)
        post.metadata["baseline_version"] = version
        post.metadata["baseline_reason"] = reason
        post.metadata["baselined_at"] = datetime.now(timezone.utc).isoformat()
        post.metadata["status"] = "baselined"

        dst.write_text(frontmatter.dumps(post), encoding="utf-8")
        return dst

    def rollback_to_baseline(self, layer: str, version: str) -> Path:
        """Restore layer workspace from a baseline."""
        baseline = self.read_baseline(layer, version)
        dst = self.get_layer_dir(layer) / "README.md"

        post = frontmatter.Post(
            content=baseline.get("content", ""),
            **{k: v for k, v in baseline.items() if k != "content"},
        )
        post.metadata["rolled_back_from"] = version
        post.metadata["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        post.metadata["status"] = "in_progress"

        dst.write_text(frontmatter.dumps(post), encoding="utf-8")
        return dst

    # ── Todo scanning ─────────────────────────────────────────

    def get_todos(self) -> list[dict[str, Any]]:
        import re

        todos: list[dict[str, Any]] = []
        manifest = self.read_manifest()
        for layer in LAYERS:
            readme_path = self.get_layer_dir(layer) / "README.md"
            if not readme_path.exists():
                continue
            post = frontmatter.load(readme_path)
            if post.metadata.get("status") == "superseded":
                continue
            # Prefer the descent at which this todo list was written
            todo_descent = post.metadata.get(
                "todo_descent", manifest.get("current_descent", 1)
            )
            for line in post.content.split("\n"):
                m = re.match(r"^\s*-\s+\[([ xX])\]\s+(.+)$", line)
                if m:
                    todos.append(
                        {
                            "layer": layer,
                            "descent": todo_descent,
                            "done": m.group(1).strip().lower() in ("x", "X"),
                            "text": m.group(2).strip(),
                        }
                    )
        return todos

    # ── Document helpers ──────────────────────────────────────

    def read_document(self, layer: str, filename: str) -> dict[str, Any]:
        path = self.get_layer_dir(layer) / filename
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {layer}/{filename}")
        post = frontmatter.load(path)
        return {**post.metadata, "content": post.content}

    def write_document(self, layer: str, filename: str, content: str, **metadata: Any) -> Path:
        path = self.get_layer_dir(layer) / filename
        meta = {
            "se_version": "2.0",
            "layer": layer,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **metadata,
        }
        if path.exists():
            old = frontmatter.load(path)
            meta.setdefault("created_at", old.metadata.get("created_at", meta["updated_at"]))
        else:
            meta.setdefault("created_at", meta["updated_at"])

        post = frontmatter.Post(content=content, **meta)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return path

    # ── Ascension history ─────────────────────────────────────

    def append_ascent_record(self, record: dict[str, Any]) -> None:
        path = self.vinw_dir / "ascensions.md"
        existing = path.read_text(encoding="utf-8")
        entry = ASCENSION_ENTRY_TEMPLATE.format(
            ascent_id=record["id"],
            created_at=record["created_at"],
            descent_before=record["descent_before"],
            from_layer=record["from_layer"],
            to_layer=record["to_layer"],
            to_baseline=record["to_baseline"],
            reason=record["reason"],
            descent_after=record["descent_after"],
        )
        path.write_text(existing + entry, encoding="utf-8")
