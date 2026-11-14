"""Atomic changelog append operations."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def _cell(value: object) -> str:
    """Escape a value for a markdown table cell.

    All line separators collapse to spaces: `str.splitlines()` on the read
    side treats \r, \v, \f, \x1c-\x1e, \x85, U+2028/2029 as breaks too, so
    only handling \n silently truncated CRLF content (r23 GAP-003).
    """
    text = "" if value is None else str(value)
    text = " ".join(text.splitlines())
    return text.replace("|", "\\|").strip()


def append_changelog_entry(
    changelog_path: Path,
    *,
    change_type: str,
    layer: str,
    descent: int,
    scope: str,
    reason: str,
    before: str = "",
    after: str = "",
    extra: dict[str, object] | None = None,
) -> str:
    """Atomically append a changelog entry. Returns the generated change_id."""
    existing = changelog_path.read_text(encoding="utf-8")

    count = len(re.findall(r"^## chg-", existing, re.MULTILINE))
    now = datetime.now(timezone.utc)
    change_id = f"chg-{now.strftime('%Y%m%d-%H%M%S')}-{count + 1:03d}"

    extra_rows = ""
    for key, value in (extra or {}).items():
        extra_rows += f"| **{_cell(key)}** | {_cell(value)} |\n"

    entry = f"""
## {change_id} [{now.isoformat()}]

| 字段 | 内容 |
|------|------|
| **变更类型** | `{_cell(change_type)}` |
| **下降轮次** | descent-{descent} |
| **层** | {_cell(layer)} |
| **范围** | `{_cell(scope)}` |
| **原因** | {_cell(reason)} |
{extra_rows}
### Before
```text
{before}
```

### After
```text
{after}
```
"""
    changelog_path.write_text(existing + entry, encoding="utf-8")
    return change_id


_CODE_FIELDS = {"变更类型", "范围"}
_BOOL_FIELDS = {"corrected"}


def read_changelog_entries(changelog_path: Path) -> list[dict[str, object]]:
    """Parse the changelog into structured entries (oldest first).

    Line-based state machine: fence tracking happens *before* heading
    detection, so a `## chg-` line or a table row pasted inside a
    ```text Before/After block cannot create a bogus entry or overwrite a
    real field (r23 GAP-001).
    """
    if not changelog_path.exists():
        return []
    content = changelog_path.read_text(encoding="utf-8")

    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## chg-"):
            if current is not None:
                entries.append(current)
            rest = line[3:].strip()
            change_id = rest.split()[0]
            current = {"id": change_id}
            m = re.search(r"\[(\d{4}-\d{2}-\d{2}T[^\]]+)\]", rest)
            if m:
                current["timestamp"] = m.group(1)
            continue
        if current is None or not line.startswith("|"):
            continue
        raw_cells = line.strip().strip("|").split("|")
        if len(raw_cells) < 2:
            continue
        key = raw_cells[0].strip().strip("* ").strip()
        value = "|".join(raw_cells[1:]).strip()
        if not key or key in ("字段", "------"):
            continue
        if key in _CODE_FIELDS:
            value = value.strip("`").strip()
        value = value.replace("\\|", "|")
        if key in _BOOL_FIELDS:
            current[key] = value == "True"
        else:
            current[key] = value
    if current is not None:
        entries.append(current)
    return entries
