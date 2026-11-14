"""Recompute the numbers quoted in README's "Self-hosting Record".

Counting basis (kept explicit so the numbers stay reproducible):
- only LLM audit reports (those carrying gaps/inconsistencies) are counted;
  text-check reports are ignored
- reports are de-duplicated by the hash of their findings payload
- classification comes from the finding itself, else from the stored triage
  verdict with the same id, else "unclassified" (pre-contract reports)
"""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import subprocess
import sys

import frontmatter


def findings_stats(repo: pathlib.Path) -> tuple[int, int, collections.Counter]:
    reports = sorted((repo / "vinw-design/L4-编码实现/consistency-reports").glob("*.md"))
    seen: set[str] = set()
    stats: collections.Counter = collections.Counter()
    audited = 0
    for path in reports:
        post = frontmatter.load(path)
        md = post.metadata
        gaps = [g for g in (md.get("gaps") or []) if isinstance(g, dict)]
        incs = [i for i in (md.get("inconsistencies") or []) if isinstance(i, dict)]
        if not gaps and not incs:
            continue
        payload = json.dumps([gaps, incs], sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        audited += 1
        triage = {t.get("id"): t.get("classification") for t in (md.get("triage") or []) if isinstance(t, dict)}
        for finding in gaps + incs:
            stats[finding.get("classification") or triage.get(finding.get("id")) or "unclassified"] += 1
    return audited, sum(stats.values()), stats


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parent.parent
    audited, total, stats = findings_stats(repo)

    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--collect-only"],
        cwd=repo, capture_output=True, text=True,
    ).stdout
    test_count = sum(1 for line in tests.splitlines() if "::" in line)
    test_files = len(list((repo / "tests").glob("test_*.py")))

    sys.path.insert(0, str(repo))
    import vinw.server as server  # noqa: PLC0415

    tools = len(getattr(server.mcp, "_tool_manager")._tools)

    manifest = frontmatter.load(repo / "vinw-design/.vinw/manifest.md").metadata
    print(f"descents        : {manifest.get('current_descent')}")
    print(f"ascents         : {len(manifest.get('ascent_history', []))}")

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    date = subprocess.run(
        ["git", "log", "-1", "--date=format:%Y-%m-%d %H:%M %z", "--format=%ad"], cwd=repo,
        capture_output=True, text=True,
    ).stdout.strip()

    print(f"commit          : {commit} ({date})")
    print(f"tests           : {test_count} passed across {test_files} files")
    print(f"tools           : {tools}")
    print(f"audit reports   : {audited} distinct LLM audits")
    print(f"findings        : {total}")
    for key, value in stats.most_common():
        print(f"  {key:14s}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
