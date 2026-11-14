"""SE-MCP v2 — Software Engineering MCP Server.

Markdown-first, spiral-ascend workflow engine for cross-harness agent projects.
"""

__version__ = "0.2.0"
__all__ = ["__version__"]


def _git(*args: str) -> str:
    import subprocess
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        return ""


_repo = _git("rev-parse", "--show-toplevel")
__commit__ = (_git("rev-parse", "HEAD") or "unknown")[:12] if _repo else "unknown"
__dirty__ = bool(_git("status", "--porcelain")) if _repo else False
# 记录源码仓库路径，供 TUI 版本比对（无源码则不可比对，防护静默降级）
__source_repo__ = _repo or None
