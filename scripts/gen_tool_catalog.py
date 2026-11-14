#!/usr/bin/env python3
"""Regenerate the MCP tool table in L3 api-design.md from vinw/server.py.

The catalogue drifted from reality repeatedly; generating it (and asserting
equality in tests/test_contract_v014.py) keeps the design honest.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "vinw" / "server.py"
DESIGN = ROOT / "vinw-design" / "L3-方案细化" / "api-design.md"


def tool_names() -> list[str]:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    return sorted(
        n.name
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name.startswith("se_")
    )


def render(names: list[str]) -> str:
    rows = "\n".join(f"| `{n}` | — | — |" for n in names)
    return (
        f"## MCP 工具清单（共 {len(names)} 个，由 scripts/gen_tool_catalog.py 生成）\n"
        "\n> 生成方式：解析 `vinw/server.py` 中所有 `se_*` 函数；"
        "`tests/test_contract_v014.py` 断言此处条目数 == 实际注册数。\n"
        "\n| 工具 | 输入 | 输出 |\n|------|------|------|\n"
        f"{rows}\n"
    )


def main() -> int:
    names = tool_names()
    text = DESIGN.read_text(encoding="utf-8")
    if "## MCP 工具清单" not in text:
        print("catalog section not found", file=sys.stderr)
        return 1

    head, rest = text.split("## MCP 工具清单", 1)
    tail = rest.split("\n## ", 1)[1] if "\n## " in rest else ""
    new = head + render(names) + "\n## " + tail
    DESIGN.write_text(new, encoding="utf-8")
    print(f"regenerated {len(names)} tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
