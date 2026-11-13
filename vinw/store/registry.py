"""Multi-project registry — JSON single-file, atomic writes, probe-based status.

Design: L3 v0.7 (descent-7). Storage lives at $VINW_HOME/registry.json
(default ~/.vinw/registry.json). Stale entries are marked, never silently
deleted: pruning requires an explicit call and defaults to dry-run.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project import Project

REGISTRY_VERSION = 1


class ProjectNotFound(LookupError):
    """Raised when a name or path cannot be resolved to a registered project."""


def vinw_home() -> Path:
    """Root for VINW global state; override with VINW_HOME (tests, sandboxes)."""
    return Path(os.environ.get("VINW_HOME", Path.home() / ".vinw")).expanduser()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def is_vinw_project(root: Path) -> bool:
    return (root / ".vinw" / "manifest.md").exists()


class ProjectRegistry:
    """Registry of VINW projects addressed by absolute path, aliased by name."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else vinw_home() / "registry.json"

    # ── Persistence ───────────────────────────────────────────

    def _empty(self) -> dict[str, Any]:
        return {"version": REGISTRY_VERSION, "projects": {}}

    def load(self) -> dict[str, Any]:
        """Read the registry; a corrupt file is backed up, never discarded."""
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            backup = self.path.with_suffix(f".json.bak-{int(datetime.now().timestamp())}")
            try:
                self.path.rename(backup)
            except OSError:
                pass
            return self._empty()

        if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
            return self._empty()
        data.setdefault("version", REGISTRY_VERSION)
        return data

    def save(self, data: dict[str, Any]) -> None:
        """Atomic write: temp file in the same dir, then os.replace."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".registry-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            os.replace(tmp_name, self.path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    # ── Queries ───────────────────────────────────────────────

    def _find_key(self, data: dict[str, Any], name_or_path: str) -> str | None:
        target = normalize(name_or_path)
        for key in data["projects"]:
            if Path(key) == target:
                return key
        for key, entry in data["projects"].items():
            if entry.get("name") == name_or_path:
                return key
        return None

    def get(self, name_or_path: str) -> dict[str, Any] | None:
        data = self.load()
        key = self._find_key(data, name_or_path)
        if key is None:
            return None
        return {"path": key, **data["projects"][key]}

    def list(self, status: str | None = None, probe: bool = True) -> list[dict[str, Any]]:
        """List entries; probe=True refreshes ok/missing status (never deletes)."""
        data = self.load()
        changed = False
        entries: list[dict[str, Any]] = []

        for key, entry in data["projects"].items():
            item = {"path": key, **entry}
            if probe:
                ok = is_vinw_project(Path(key))
                item["status"] = "ok" if ok else "missing"
                if ok:
                    if entry.get("missing_since") is not None or entry.get("last_seen_ok") is None:
                        entry["last_seen_ok"] = _now()
                        entry["missing_since"] = None
                        changed = True
                else:
                    item["status"] = "missing"
                    if entry.get("missing_since") is None:
                        entry["missing_since"] = _now()
                        changed = True
            entries.append(item)

        if changed:
            self.save(data)

        if status:
            entries = [e for e in entries if e.get("status") == status]
        return sorted(entries, key=lambda e: e.get("name") or e["path"])

    # ── Mutations ─────────────────────────────────────────────

    def add(self, path: str | Path, name: str | None = None) -> dict[str, Any]:
        """Register a project; returns {path, name, status, warning?}."""
        root = normalize(path)
        if not is_vinw_project(root):
            raise ValueError(
                f"{root} 不是 VINW 工程（缺少 .vinw/manifest.md）"
            )

        data = self.load()
        key = str(root)
        manifest_name = _manifest_name(root)
        desired = name or manifest_name or root.name

        warning = None
        if key not in data["projects"]:
            existing_names = {e.get("name") for e in data["projects"].values()}
            base = desired
            suffix = 2
            while desired in existing_names:
                desired = f"{base}-{suffix}"
                warning = f"名称 {base} 已被占用，登记为 {desired}"
                suffix += 1

        entry = data["projects"].get(key, {})
        entry.update(
            {
                "name": desired,
                "last_accessed_at": entry.get("last_accessed_at") or _now(),
                "last_seen_ok": _now(),
                "missing_since": None,
            }
        )
        entry.setdefault("added_at", _now())
        data["projects"][key] = entry
        self.save(data)

        result = {"registered": True, "path": key, "name": desired, "status": "ok"}
        if warning:
            result["warning"] = warning
        return result

    def remove(self, name_or_path: str) -> dict[str, Any]:
        """Remove a registration entry (disk content is untouched)."""
        data = self.load()
        key = self._find_key(data, name_or_path)
        if key is None:
            raise ProjectNotFound(f"未找到工程: {name_or_path}")
        entry = data["projects"].pop(key)
        self.save(data)
        return {"removed": True, "name": entry.get("name"), "path": key}

    def prune(self, missing_only: bool = True, force: bool = False) -> dict[str, Any]:
        """Delete stale entries. force=False is a dry run (default)."""
        data = self.load()
        doomed: list[str] = []
        for key, entry in data["projects"].items():
            if missing_only and is_vinw_project(Path(key)):
                continue
            doomed.append(key)

        names = {k: data["projects"][k].get("name") for k in doomed}
        if force:
            for key in doomed:
                del data["projects"][key]
            self.save(data)

        return {
            "dry_run": not force,
            "pruned": len(doomed) if force else 0,
            "would_prune": doomed if not force else [],
            "candidates": names,
        }

    def touch(self, name_or_path: str) -> None:
        data = self.load()
        key = self._find_key(data, name_or_path)
        if key is not None:
            data["projects"][key]["last_accessed_at"] = _now()
            self.save(data)

    # ── Resolution ────────────────────────────────────────────

    def resolve(self, name_or_path: str | None) -> Project:
        """Resolve a path or registered name to a Project.

        Order: existing path → registry name/path → raise ProjectNotFound.
        """
        if not name_or_path:
            raise ProjectNotFound("project 参数为空")

        candidate = Path(name_or_path).expanduser()
        if candidate.exists():
            root = candidate.resolve()
            if is_vinw_project(root):
                return Project(root)

        entry = self.get(name_or_path)
        if entry is not None:
            root = Path(entry["path"])
            if is_vinw_project(root):
                return Project(root)
            raise ProjectNotFound(
                f"工程 {entry.get('name')} 的路径已失效: {root}"
                f"（可用 se_prune_projects 清理登记）"
            )

        raise ProjectNotFound(f"未找到工程: {name_or_path}")

    def describe(self) -> list[str]:
        """Short labels for error messages."""
        return [e.get("name") or e["path"] for e in self.list(probe=False)]


def _manifest_name(root: Path) -> str | None:
    import frontmatter

    try:
        post = frontmatter.load(root / ".vinw" / "manifest.md")
        return post.metadata.get("name")
    except Exception:
        return None
