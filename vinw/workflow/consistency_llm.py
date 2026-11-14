"""LLM-based design-code consistency auditor."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter

from ..store.project import Project
from .symbols import (
    DEFAULT_CODE_EXTENSIONS,
    extract_code_symbols_with_lines,
    is_code_file,
    split_design_symbols,
)

# Directories never scanned for code
_EXCLUDED_DIR_PARTS = {".venv", "build", "node_modules", "__pycache__", ".git"}


def _resolve_code_root(project: Project) -> Path:
    """Resolve the code repository root.

    manifest may declare `code_root` relative to the project root
    (self-hosting: design project lives inside the code repo, e.g. "..").
    Defaults to the project root itself.
    """
    manifest = project.read_manifest()
    code_root_meta = manifest.get("code_root")
    if code_root_meta:
        return (project.root / str(code_root_meta)).resolve()
    return project.root


def code_extensions(project: Project) -> list[str]:
    """Extensions to scan, from manifest `code_extensions` or the default set."""
    manifest = project.read_manifest()
    configured = manifest.get("code_extensions")
    if isinstance(configured, list) and configured:
        return [str(e) for e in configured]
    return list(DEFAULT_CODE_EXTENSIONS)


def _collect_code_files(
    code_root: Path,
    code_scope: list[str] | None,
    extensions: list[str] | None = None,
) -> list[Path]:
    """Collect code files; code_scope entries may be files or directories."""
    if code_scope:
        candidates = [code_root / p for p in code_scope]
    else:
        candidates = [code_root / "src"] if (code_root / "src").exists() else [code_root]

    exts = extensions or DEFAULT_CODE_EXTENSIONS
    files: list[Path] = []
    for c in candidates:
        if c.is_file() and is_code_file(c, exts):
            files.append(c)
        elif c.is_dir():
            for candidate in c.rglob("*"):
                if candidate.is_file() and is_code_file(candidate, exts):
                    files.append(candidate)

    return [
        f
        for f in files
        if ".baseline" not in str(f)
        and not any(part in _EXCLUDED_DIR_PARTS for part in f.parts)
    ]


def file_hashes(code_root: Path, code_scope: list[str] | None = None) -> dict[str, str]:
    """sha256 per scanned code file, keyed by path relative to code_root."""
    result: dict[str, str] = {}
    for f in _collect_code_files(code_root, code_scope):
        try:
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            continue
        result[_display_path(code_root, f)] = digest
    return result


def design_hash(design_path: Path) -> str:
    """Digest of a single design document."""
    try:
        return hashlib.sha256(design_path.read_bytes()).hexdigest()
    except OSError:
        return ""


def layer_design_hash(layer_dir: Path) -> str:
    """Digest over the layer's *design* documents.

    README.md carries workflow state (status, todos, baseline table), so it is
    excluded: mirroring a status must not look like a design change.
    """
    if not layer_dir.exists():
        return ""
    digest = hashlib.sha256()
    for path in sorted(layer_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        digest.update(path.name.encode())
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def aggregate_fingerprint(hashes: dict[str, str], design_digest: str) -> str:
    payload = "|".join(f"{k}:{v}" for k, v in sorted(hashes.items()))
    return hashlib.sha256(f"{payload}||{design_digest}".encode()).hexdigest()


def _symbol_lines(content: str, names: set[str]) -> dict[str, int]:
    """First 1-based line where a design symbol is mentioned."""
    lines: dict[str, int] = {}
    for idx, line in enumerate(content.splitlines(), 1):
        for name in names:
            if name not in lines and name in line:
                lines[name] = idx
    return lines


def _display_path(code_root: Path, code_file: Path) -> str:
    try:
        return str(code_file.relative_to(code_root))
    except ValueError:
        return str(code_file)


PROMPT_TEMPLATE = """你是一名独立的软件工程审查者（reviewer），与被审代码的作者不是同一主体。任务是对照【设计文档】审查【代码与测试】，**不要回答"是否一致"**，而是产出可核查的证据清单。

## A. 缺口清单（gaps）
逐条列出「设计要求了，但缺少代码实现或缺少测试覆盖」的条目。

## B. 实现一致性（inconsistencies）
检查代码在**逻辑、数据结构、接口签名、约束条件**上是否与设计一致。重点关注：
1. 控制流/分块/并行策略是否与设计描述一致
2. 数据结构布局（如打包布局 [MC/MR][KC][MR]）是否与设计一致
3. 接口签名、参数顺序、返回类型、错误码是否一致
4. 数值/参量约束（分块参数、容差、阈值）是否与设计一致
5. 设计中声明但未实现的分支、参数、边界处理

## 证据要求
每条结论必须给出 `design_ref`（文件:行）与 `code_ref`（文件:行）；确实无对应实现时写 `"code_ref": "无对应实现"`。
无行号证据的条目视为无效，不要输出。

严格按以下 JSON 输出，不要添加额外说明：

```json
{
  "overall": "passed" | "warning" | "failed",
  "gaps": [
    {"id": "GAP-001", "design_ref": "file:line", "missing": "code" | "test",
     "description": "...", "severity": "critical" | "warning"}
  ],
  "inconsistencies": [
    {"id": "INC-001", "category": "logic" | "data_model" | "interface" | "constraint",
     "design_ref": "file:line", "code_ref": "file:line",
     "description": "...", "suggestion": "..."}
  ],
  "matched": [
    {"design_ref": "file:line", "code_ref": "file:line", "symbol": "...", "note": "..."}
  ]
}
```

=== 设计文档 ===
{design_content}

=== 代码与测试 ===
{code_content}

=== 审查开始（只输出 JSON） ===
"""


class LLMConsistencyAuditor:
    """Use LLM to perform semantic consistency audit between design and code."""

    def __init__(self, project: Project):
        self.project = project

    def audit(
        self,
        design_layer: str = "L3-方案细化",
        design_doc: str = "api-design.md",
        code_scope: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Read design document and code files, construct LLM prompt,
        return structured consistency report.
        
        NOTE: This method prepares the prompt and returns it along with
        file contents. The actual LLM call should be made by the caller
        (agent harness) since we don't have direct LLM access in the MCP server.
        """
        design_path = self.project.get_layer_dir(design_layer) / design_doc
        if not design_path.exists():
            return {"error": f"Design doc {design_layer}/{design_doc} not found"}

        design_content = design_path.read_text(encoding="utf-8")

        # Collect code files
        code_root = _resolve_code_root(self.project)
        code_files = _collect_code_files(code_root, code_scope, code_extensions(self.project))

        code_contents: list[str] = []
        for code_file in code_files:
            code = code_file.read_text(encoding="utf-8")
            code_contents.append(
                f"--- {_display_path(code_root, code_file)} ---\n{code}"
            )

        if not code_contents:
            return {
                "error": "No code files found in specified scope",
                "design_doc": str(design_path.relative_to(self.project.root)),
            }

        code_content = "\n\n".join(code_contents)

        # Truncate if too long (rough heuristic: 8k tokens ~ 32k chars)
        max_design = 15000
        max_code = 25000
        if len(design_content) > max_design:
            design_content = design_content[:max_design] + "\n... [truncated]"
        if len(code_content) > max_code:
            code_content = code_content[:max_code] + "\n... [truncated]"

        # Use safe string replacement (not .format) because design/code may contain { }
        prompt = PROMPT_TEMPLATE.replace("{design_content}", design_content).replace("{code_content}", code_content)

        return {
            "design_doc": str(design_path.relative_to(self.project.root)),
            "code_files_scanned": len(code_contents),
            "prompt": prompt,
            "status": "prompt_ready",
            "note": "Pass this prompt to LLM and parse the JSON response",
        }

    def store_report(
        self,
        report_data: dict[str, Any],
        report_id: str | None = None,
        *,
        descent: int | None = None,
        scope: list[str] | None = None,
        design_digest: str = "",
        hashes: dict[str, str] | None = None,
        kind: str = "text",
        policy: str | None = None,
        auditor: str | None = None,
        auditor_model: str | None = None,
        files_scanned: int | None = None,
        extensions: list[str] | None = None,
        code_symbols_count: int | None = None,
    ) -> Path:
        """Store a parsed LLM consistency report into the project."""
        if report_id is None:
            import hashlib

            # Content hash alone would collide on repeated identical verdicts and
            # overwrite an existing report (losing its triage state).
            digest = hashlib.sha256(str(report_data).encode()).hexdigest()[:8]
            # Same content must still get a fresh slot: reports double as the
            # carrier of triage state, so overwriting would lose decisions.
            reports_dir = self.project.get_layer_dir("L4-编码实现") / "consistency-reports"
            seq = 1
            if reports_dir.exists():
                seq = len(list(reports_dir.glob(f"report-{digest}-*.md"))) + 1
            report_id = f"{digest}-{seq:02d}"

        layer_dir = self.project.get_layer_dir("L4-编码实现")
        reports_dir = layer_dir / "consistency-reports"
        reports_dir.mkdir(exist_ok=True)

        report_path = reports_dir / f"report-{report_id}.md"

        inconsistencies = report_data.get("inconsistencies", [])
        matched = report_data.get("matched", [])
        overall = report_data.get("overall", "unknown")

        inc_table = "| ID | 严重程度 | 类别 | 设计引用 | 代码引用 | 描述 | 建议 |\n"
        inc_table += "|----|---------|------|---------|---------|------|------|\n"
        for inc in inconsistencies:
            inc_table += (
                f"| {inc.get('id', '-')} | {inc.get('severity', '-')} | "
                f"{inc.get('category', '-')} | {inc.get('design_ref', '-')} | "
                f"{inc.get('code_ref', '-')} | {inc.get('description', '-')} | "
                f"{inc.get('suggestion', '-')} |\n"
            )

        if not inconsistencies:
            inc_table += "| — | — | — | — | — | 无不一致项 | — |\n"

        matched_table = "| 设计引用 | 代码引用 | 符号 | 说明 |\n"
        matched_table += "|---------|---------|------|------|\n"
        for m in matched:
            matched_table += (
                f"| {m.get('design_ref', '-')} | {m.get('code_ref', '-')} | "
                f"{m.get('symbol', '-')} | {m.get('note', '-')} |\n"
            )

        if not matched:
            matched_table += "| — | — | — | — |\n"

        fingerprint = aggregate_fingerprint(hashes or {}, design_digest)

        body = f"""
# 一致性检查报告 ({report_id})

## 执行摘要

| 指标 | 数值 |
|------|------|
| 总体状态 | {overall} |
| 不一致项 | {len(inconsistencies)} |
| 匹配项 | {len(matched)} |

## 不一致项

{inc_table}

## 匹配项

{matched_table}

## 处理记录

<!-- 每条不一致项修复后在此追加：
- [x] INC-001: 修复说明 (chg-xxx)
-->
"""

        # Metadata goes through yaml.dump so nested structures stay valid YAML
        metadata: dict[str, Any] = {
            "se_version": "2.0",
            "layer": "L4-编码实现",
            "doc_type": "consistency-report",
            "report_id": report_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall,
            "code_fingerprint": fingerprint,
            "kind": kind,
        }
        if policy:
            metadata["policy"] = policy
        if auditor:
            metadata["auditor"] = auditor
        if auditor_model:
            metadata["auditor_model"] = auditor_model
        gaps = report_data.get("gaps")
        if gaps:
            metadata["gaps"] = gaps
            metadata["gaps_count"] = len(gaps)
        if inconsistencies:
            # Machine-readable findings: triage needs them, not just the table
            metadata["inconsistencies"] = [
                {
                    "id": inc.get("id"),
                    "severity": inc.get("severity"),
                    "category": inc.get("category"),
                    "design_ref": inc.get("design_ref"),
                    "code_ref": inc.get("code_ref"),
                    "description": inc.get("description"),
                    "suggestion": inc.get("suggestion"),
                }
                for inc in inconsistencies
            ]
            metadata["inconsistencies_count"] = len(inconsistencies)
        if kind == "llm":
            metadata["llm_verdict"] = overall
        if files_scanned is not None:
            metadata["files_scanned"] = files_scanned
        if extensions:
            metadata["extensions"] = list(extensions)
        if code_symbols_count is not None:
            metadata["code_symbols_count"] = code_symbols_count
        if descent is not None:
            metadata["descent"] = descent
        if scope:
            metadata["scope"] = list(scope)
        if design_digest:
            metadata["design_hash"] = design_digest
        if hashes:
            metadata["file_hashes"] = dict(hashes)

        content = frontmatter.dumps(frontmatter.Post(body.strip() + "\n", **metadata))
        report_path.write_text(content, encoding="utf-8")
        return report_path


class TextConsistencyChecker:
    """Fallback: simple text-based existence check (no LLM required)."""

    def __init__(self, project: Project):
        self.project = project

    def check(
        self,
        design_layer: str = "L3-方案细化",
        design_doc: str = "api-design.md",
        code_scope: list[str] | None = None,
    ) -> dict[str, Any]:
        design_path = self.project.get_layer_dir(design_layer) / design_doc
        if not design_path.exists():
            return {"error": f"Design doc {design_layer}/{design_doc} not found"}

        design_content = design_path.read_text(encoding="utf-8")
        exts = code_extensions(self.project)

        code_root = _resolve_code_root(self.project)
        code_files = _collect_code_files(code_root, code_scope, exts)

        # An empty scan is a configuration problem, not a pass: reporting
        # "everything is missing" would be actively misleading.
        if not code_files:
            return {
                "error": "no code files matched the configured extensions",
                "code_root": str(code_root),
                "code_scope": code_scope or [],
                "extensions": exts,
                "hint": "在 manifest 配置 code_extensions / code_root，或检查 code_scope",
            }

        # Only API-surface mentions are blocking; config keys / enum values
        # and prose mentions are advisory (reported, never blocking).
        design_symbols, advisory_symbols = split_design_symbols(design_content)
        design_lines = _symbol_lines(design_content, design_symbols)
        code_symbol_map: dict[str, str] = {}
        for code_file in code_files:
            rel = _display_path(code_root, code_file)
            for name, line in extract_code_symbols_with_lines(code_file, exts).items():
                code_symbol_map.setdefault(name, f"{rel}:{line}")

        matched: list[dict[str, Any]] = []
        inconsistencies: list[dict[str, Any]] = []
        for name in sorted(design_symbols):
            if name in code_symbol_map:
                matched.append(
                    {
                        "design_ref": f"{design_doc}:{design_lines.get(name, 0)}",
                        "code_ref": code_symbol_map[name],
                        "symbol": name,
                        "note": "Symbol defined in code",
                    }
                )
            else:
                inconsistencies.append(
                    {
                        "id": f"INC-{len(inconsistencies) + 1:03d}",
                        "severity": "warning",
                        "category": "missing",
                        "design_ref": f"{design_doc}:{design_lines.get(name, 0)}",
                        "code_ref": "无对应实现",
                        "description": f"Design symbol '{name}' not found in code",
                        "suggestion": f"Implement {name} or remove it from the design doc",
                    }
                )

        advisory_missing = sorted(advisory_symbols - set(code_symbol_map))
        overall = "passed" if not inconsistencies else "warning"

        return {
            "design_doc": str(design_path.relative_to(self.project.root)),
            "method": "text",
            "files_scanned": len(code_files),
            "extensions": exts,
            "code_symbols_count": len(code_symbol_map),
            "design_symbols_found": len(design_symbols),
            "advisory_symbols_found": len(advisory_symbols),
            "advisory_missing": advisory_missing,
            "matched": matched,
            "inconsistencies": inconsistencies,
            "overall": overall,
        }

    def _extract_symbols(self, content: str) -> list[dict[str, str]]:
        """Extract probable API symbols from markdown."""
        symbols = []
        lines = content.split("\n")

        # Pattern 1: markdown code blocks with def/class
        for i, line in enumerate(lines, 1):
            m = re.search(r"(?:def|class)\s+(\w+)", line)
            if m:
                symbols.append({"name": m.group(1), "source": f"code block L{i}"})

        # Pattern 2: table cells that look like function signatures
        # Skip header rows (contain "---" or all uppercase/short words)
        for i, line in enumerate(lines, 1):
            if "|" in line and "---" not in line:
                cells = [c.strip() for c in line.split("|")]
                for cell in cells:
                    # Match patterns like: readDoc(path: str) -> Doc
                    m = re.match(r"^([a-z_]\w*)\s*\(", cell)
                    if m and m.group(1) not in ("def", "if", "for", "while"):
                        symbols.append({"name": m.group(1), "source": f"table L{i}"})

        # Pattern 3: tool names from api-design tables (backtick-quoted or standalone)
        for i, line in enumerate(lines, 1):
            # Match backtick-quoted tool names: `se_xxx` or se_xxx in table cells
            for m in re.finditer(r"`?(se_[a-z_]+)`?", line):
                name = m.group(1)
                # Skip if it's just a column header word
                if name not in ("se_version", "vinw") and len(name) > 4:
                    symbols.append({"name": name, "source": f"api ref L{i}"})

        # Deduplicate
        seen = set()
        unique = []
        for s in symbols:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique.append(s)
        return unique
