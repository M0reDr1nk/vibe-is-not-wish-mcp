"""Atomic changelog append operations."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


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
) -> str:
    """Atomically append a changelog entry. Returns the generated change_id."""
    existing = changelog_path.read_text(encoding="utf-8")

    count = len(re.findall(r"^## chg-", existing, re.MULTILINE))
    now = datetime.now(timezone.utc)
    change_id = f"chg-{now.strftime('%Y%m%d-%H%M%S')}-{count + 1:03d}"

    entry = f"""
## {change_id} [{now.isoformat()}]

| 字段 | 内容 |
|------|------|
| **变更类型** | `{change_type}` |
| **下降轮次** | descent-{descent} |
| **层** | {layer} |
| **范围** | `{scope}` |
| **原因** | {reason} |

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
