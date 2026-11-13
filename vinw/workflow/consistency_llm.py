"""LLM-based design-code consistency auditor."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..store.project import Project


PROMPT_TEMPLATE = """你是一名严格的软件工程审计员。你的任务是对比【设计文档】与【代码实现】，找出两者之间的所有不一致，包括：

1. 接口签名不一致：函数名、参数列表、返回类型、异常声明
2. 数据模型不一致：字段名、类型、约束、默认值
3. 流程/逻辑不一致：设计描述的步骤与代码实现不符
4. 命名不一致：设计中的概念名与代码中的变量/类名不匹配
5. 约束不一致：设计中的限制条件（如缓存时间、并发数）在代码中未体现或数值错误
6. 缺失实现：设计中有定义但代码中未实现的功能
7. 多余实现：代码中有但设计中未定义的功能

请严格按照以下格式输出，不要添加任何额外说明：

```json
{
  "overall": "passed" | "warning" | "failed",
  "inconsistencies": [
    {
      "id": "INC-001",
      "severity": "critical" | "warning" | "info",
      "category": "interface" | "data_model" | "logic" | "naming" | "constraint" | "missing" | "extra",
      "design_ref": "设计文档中的具体位置或引用",
      "code_ref": "代码中的具体文件和行号",
      "description": "不一致的详细描述",
      "suggestion": "建议的修复方案"
    }
  ],
  "matched": [
    {
      "design_ref": "...",
      "code_ref": "...",
      "symbol": "...",
      "note": "匹配说明"
    }
  ]
}
```

=== 设计文档 ===
{design_content}

=== 代码 ===
{code_content}

=== 审计开始 ===
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
        code_root = self.project.root
        search_paths = [code_root / "src"] if (code_root / "src").exists() else [code_root]
        if code_scope:
            search_paths = [code_root / p for p in code_scope]

        code_contents: list[str] = []
        for spath in search_paths:
            if not spath.exists():
                continue
            for code_file in spath.rglob("*.py"):
                if ".baseline" in str(code_file):
                    continue
                code = code_file.read_text(encoding="utf-8")
                code_contents.append(
                    f"--- {code_file.relative_to(code_root)} ---\n{code}"
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
    ) -> Path:
        """Store a parsed LLM consistency report into the project."""
        if report_id is None:
            import hashlib
            report_id = hashlib.sha256(
                str(report_data).encode()
            ).hexdigest()[:8]

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

        content = f"""---
se_version: "2.0"
layer: "L4-编码实现"
doc_type: "consistency-report"
report_id: "{report_id}"
checked_at: "{datetime.now(timezone.utc).isoformat()}"
overall_status: "{overall}"
---

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

        # Extract function/class/method names from design doc
        design_symbols = self._extract_symbols(design_content)

        # Search in code
        code_root = self.project.root
        search_paths = [code_root / "src"] if (code_root / "src").exists() else [code_root]
        if code_scope:
            search_paths = [code_root / p for p in code_scope]

        inconsistencies: list[dict[str, Any]] = []
        matched: list[dict[str, Any]] = []

        for sym in design_symbols:
            found = False
            for spath in search_paths:
                if not spath.exists():
                    continue
                for code_file in spath.rglob("*.py"):
                    if ".baseline" in str(code_file):
                        continue
                    code = code_file.read_text(encoding="utf-8")
                    if sym["name"] in code:
                        found = True
                        matched.append(
                            {
                                "design_ref": f"{design_doc} (table/cell)",
                                "code_ref": str(code_file.relative_to(code_root)),
                                "symbol": sym["name"],
                                "note": "Name exists in code",
                            }
                        )
                        break
                if found:
                    break
            if not found:
                inconsistencies.append(
                    {
                        "id": f"INC-{len(inconsistencies)+1:03d}",
                        "severity": "warning",
                        "category": "missing",
                        "design_ref": sym["source"],
                        "code_ref": "N/A",
                        "description": f"Design symbol '{sym['name']}' not found in code",
                        "suggestion": f"Implement {sym['name']} or update design doc",
                    }
                )

        overall = "passed" if not inconsistencies else "warning"

        return {
            "design_doc": str(design_path.relative_to(code_root)),
            "method": "text",
            "design_symbols_found": len(design_symbols),
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
