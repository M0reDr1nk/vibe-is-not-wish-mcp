"""Atomic changelog append operations."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def _cell(value: object) -> str:
    """Escape a value for a markdown table cell (pipes and newlines)."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


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
| **变更类型** | `{change_type}` |
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


def read_changelog_entries(changelog_path: Path) -> list[dict[str, object]]:
    """Parse the changelog into structured entries (oldest first).

    Entries are markdown tables; parsing them here keeps the TUI and any
    machine consumer on one implementation instead of ad-hoc regexes
    (R33-2: alignment entries used to be unparseable free text).
    """
    import frontmatter  # noqa: F401  (kept out of the hot path below)

    if not changelog_path.exists():
        return []
    content = changelog_path.read_text(encoding="utf-8")
    blocks = re.split(r"^## (chg-\S+)([^\n]*)$", content, flags=re.MULTILINE)
    entries: list[dict[str, object]] = []
    for i in range(1, len(blocks), 3):
        change_id = blocks[i]
        title_rest = blocks[i + 1] if i + 1 < len(blocks) else ""
        body = blocks[i + 2] if i + 2 < len(blocks) else ""
        record: dict[str, object] = {"id": change_id}
        m = re.search(r"\[(\d{4}-\d{2}-\d{2}T[^\]]+)\]", title_rest)
        if m:
            record["timestamp"] = m.group(1)
        for line in body.splitlines():
            if not line.startswith("|"):
                continue
            raw_cells = line.strip().strip("|").split("|")
            if len(raw_cells) < 2:
                continue
            key = raw_cells[0].strip().strip("* ").strip()
            value = "|".join(raw_cells[1:]).strip().strip("`").strip()
            value = value.replace("\\|", "|")
            if not key or key in ("字段", "------"):
                continue
            record[key] = value
        entries.append(record)
    return entries
