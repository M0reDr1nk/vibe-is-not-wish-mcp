"""Multi-project registry — SQLite control plane (L3 v0.8).

Control plane (this module): which projects exist, their declared state
(active/dormant), observed availability, and a state-transition log.
Data plane (unchanged): each project's own Markdown under `<root>/.vinw/`.

Storage: `$VINW_HOME/registry.db` (default `~/.vinw/registry.db`), WAL mode.
Design rationale (control plane vs data plane, and why not JSON/CSV):
docs/L2 synthesis for descent-8.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .project import Project

SCHEMA_VERSION = 2

VALID_STATES = ("active", "dormant")


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
    """SQLite-backed registry: path is the key, name is a unique alias."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else vinw_home() / "registry.db"
        # Legacy JSON location, migrated on first open
        self.legacy_json = self.path.with_suffix(".json")

    # ── Connection / schema ───────────────────────────────────

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._quarantine_if_corrupt()
        conn = sqlite3.connect(str(self.path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            self._ensure_schema(conn)
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _quarantine_if_corrupt(self) -> None:
        """A corrupt DB is renamed aside (never deleted), then recreated."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        try:
            probe = sqlite3.connect(str(self.path), timeout=2.0)
            try:
                probe.execute("PRAGMA user_version").fetchone()
            finally:
                probe.close()
        except sqlite3.DatabaseError:
            import sys

            backup = self.path.with_suffix(
                f".db.corrupt-{int(datetime.now().timestamp())}"
            )
            try:
                self.path.rename(backup)
                print(
                    f"warning: registry 损坏，已备份为 {backup.name} 并重建",
                    file=sys.stderr,
                )
            except OSError:
                pass

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION:
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              path             TEXT PRIMARY KEY,
              name             TEXT NOT NULL UNIQUE,
              state            TEXT NOT NULL DEFAULT 'active'
                                 CHECK (state IN ('active','dormant')),
              added_at         TEXT NOT NULL,
              last_accessed_at TEXT,
              last_seen_ok     TEXT,
              missing_since    TEXT
            );
            CREATE TABLE IF NOT EXISTS project_events (
              id     INTEGER PRIMARY KEY AUTOINCREMENT,
              path   TEXT NOT NULL,
              event  TEXT NOT NULL,
              at     TEXT NOT NULL,
              detail TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_path
              ON project_events(path, id DESC);
            """
        )
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self._migrate_legacy_json(conn)

    def _migrate_legacy_json(self, conn: sqlite3.Connection) -> None:
        """Import a legacy registry.json once, keeping the file as a backup."""
        if not self.legacy_json.exists():
            return
        if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] > 0:
            return
        try:
            data = json.loads(self.legacy_json.read_text(encoding="utf-8"))
            projects = data.get("projects", {})
        except (json.JSONDecodeError, OSError):
            return

        now = _now()
        for path, entry in projects.items():
            conn.execute(
                """INSERT OR IGNORE INTO projects
                   (path, name, state, added_at, last_accessed_at,
                    last_seen_ok, missing_since)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    path,
                    entry.get("name") or Path(path).name,
                    "active",
                    entry.get("added_at") or now,
                    entry.get("last_accessed_at"),
                    entry.get("last_seen_ok"),
                    entry.get("missing_since"),
                ),
            )
            self._log_event(conn, path, "import", f"from {self.legacy_json.name}")
        conn.commit()

        backup = self.legacy_json.with_suffix(
            f".json.migrated-{int(datetime.now().timestamp())}"
        )
        try:
            self.legacy_json.rename(backup)
        except OSError:
            pass

    @staticmethod
    def _log_event(
        conn: sqlite3.Connection, path: str, event: str, detail: str | None = None
    ) -> None:
        conn.execute(
            "INSERT INTO project_events (path, event, at, detail) VALUES (?,?,?,?)",
            (path, event, _now(), detail),
        )

    # ── Row helpers ───────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> dict[str, Any]:
        entry = dict(row)
        ok = is_vinw_project(Path(entry["path"]))
        entry["status"] = "ok" if ok else "missing"
        return entry

    @staticmethod
    def _find_path(conn: sqlite3.Connection, name_or_path: str) -> str | None:
        target = str(normalize(name_or_path))
        row = conn.execute(
            "SELECT path FROM projects WHERE path = ?", (target,)
        ).fetchone()
        if row:
            return row["path"]
        row = conn.execute(
            "SELECT path FROM projects WHERE name = ?", (name_or_path,)
        ).fetchone()
        return row["path"] if row else None

    # ── Queries ───────────────────────────────────────────────

    def get(self, name_or_path: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            path = self._find_path(conn, name_or_path)
            if path is None:
                return None
            row = conn.execute(
                "SELECT * FROM projects WHERE path = ?", (path,)
            ).fetchone()
            return self._row_to_entry(row)

    def list(
        self, status: str | None = None, probe: bool | None = None
    ) -> list[dict[str, Any]]:
        """List entries.

        probe=None (default): probe only `active` projects; dormant ones keep
        cached values and are marked `probed: False`.
        probe=True: probe everything. probe=False: probe nothing.
        """
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM projects").fetchall()
            entries: list[dict[str, Any]] = []

            for row in rows:
                entry = dict(row)
                should_probe = (
                    True if probe is True else False if probe is False else entry["state"] == "active"
                )
                if not should_probe:
                    cached_ok = entry["missing_since"] is None
                    entry["status"] = "ok" if cached_ok else "missing"
                    entry["probed"] = False
                    entries.append(entry)
                    continue

                ok = is_vinw_project(Path(entry["path"]))
                entry["status"] = "ok" if ok else "missing"
                entry["probed"] = True
                self._record_probe(conn, entry, ok)
                entries.append(entry)

            if status:
                entries = [e for e in entries if e.get("status") == status]

        return sorted(entries, key=lambda e: e.get("name") or e["path"])

    def _record_probe(
        self, conn: sqlite3.Connection, entry: dict[str, Any], ok: bool
    ) -> None:
        path = entry["path"]
        if ok:
            if entry["missing_since"] is not None:
                conn.execute(
                    "UPDATE projects SET last_seen_ok=?, missing_since=NULL WHERE path=?",
                    (_now(), path),
                )
                self._log_event(conn, path, "recover", "path reachable again")
        elif entry["missing_since"] is None:
            now = _now()
            conn.execute(
                "UPDATE projects SET missing_since=? WHERE path=?", (now, path)
            )
            self._log_event(conn, path, "missing", "path not a VINW project")

    # ── Mutations ─────────────────────────────────────────────

    def add(self, path: str | Path, name: str | None = None) -> dict[str, Any]:
        root = normalize(path)
        if not is_vinw_project(root):
            raise ValueError(f"{root} 不是 VINW 工程（缺少 .vinw/manifest.md）")

        key = str(root)
        desired = name or _manifest_name(root) or root.name
        warning = None

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT name FROM projects WHERE path = ?", (key,)
            ).fetchone()

            if existing is None:
                taken = {
                    r["name"] for r in conn.execute("SELECT name FROM projects")
                }
                base = desired
                suffix = 2
                while desired in taken:
                    desired = f"{base}-{suffix}"
                    warning = f"名称 {base} 已被占用，登记为 {desired}"
                    suffix += 1
                now = _now()
                conn.execute(
                    """INSERT INTO projects
                       (path, name, state, added_at, last_accessed_at, last_seen_ok)
                       VALUES (?,?,?,?,?,?)""",
                    (key, desired, "active", now, now, now),
                )
                self._log_event(conn, key, "register", desired)
            else:
                desired = existing["name"]
                conn.execute(
                    "UPDATE projects SET last_seen_ok=?, missing_since=NULL WHERE path=?",
                    (_now(), key),
                )

        result = {"registered": True, "path": key, "name": desired, "status": "ok"}
        if warning:
            result["warning"] = warning
        return result

    def remove(self, name_or_path: str) -> dict[str, Any]:
        with self._connect() as conn:
            path = self._find_path(conn, name_or_path)
            if path is None:
                raise ProjectNotFound(f"未找到工程: {name_or_path}")
            row = conn.execute(
                "SELECT name FROM projects WHERE path = ?", (path,)
            ).fetchone()
            conn.execute("DELETE FROM projects WHERE path = ?", (path,))
            self._log_event(conn, path, "remove")
            return {"removed": True, "name": row["name"], "path": path}

    def set_state(self, name_or_path: str, state: str) -> dict[str, Any]:
        """Declare a project active or dormant (intent, not observation)."""
        if state not in VALID_STATES:
            raise ValueError(f"state 必须是 {VALID_STATES}")
        with self._connect() as conn:
            path = self._find_path(conn, name_or_path)
            if path is None:
                raise ProjectNotFound(f"未找到工程: {name_or_path}")
            conn.execute("UPDATE projects SET state=? WHERE path=?", (state, path))
            self._log_event(conn, path, "activate" if state == "active" else "deactivate")
            row = conn.execute(
                "SELECT name FROM projects WHERE path=?", (path,)
            ).fetchone()
        return {"name": row["name"], "path": path, "state": state}

    def prune(self, missing_only: bool = True, force: bool = False) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path, name FROM projects").fetchall()
            doomed = [
                r["path"]
                for r in rows
                if not (missing_only and is_vinw_project(Path(r["path"])))
            ]
            names = {r["path"]: r["name"] for r in rows if r["path"] in doomed}

            if force:
                for path in doomed:
                    conn.execute("DELETE FROM projects WHERE path=?", (path,))
                    self._log_event(conn, path, "remove", "pruned (path missing)")

        return {
            "dry_run": not force,
            "pruned": len(doomed) if force else 0,
            "would_prune": [] if force else doomed,
            "candidates": names,
        }

    def touch(self, name_or_path: str) -> None:
        """Single-row UPDATE — no whole-file rewrite, no debouncing needed."""
        with self._connect() as conn:
            path = self._find_path(conn, name_or_path)
            if path is not None:
                conn.execute(
                    "UPDATE projects SET last_accessed_at=? WHERE path=?",
                    (_now(), path),
                )

    # ── History / export ──────────────────────────────────────

    def history(self, name_or_path: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            path = self._find_path(conn, name_or_path)
            if path is None:
                raise ProjectNotFound(f"未找到工程: {name_or_path}")
            rows = conn.execute(
                """SELECT event, at, detail FROM project_events
                   WHERE path=? ORDER BY id DESC LIMIT ?""",
                (path, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def export_json(self) -> dict[str, Any]:
        """Human-readable snapshot for review or backup (not read back)."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
            return {
                "version": SCHEMA_VERSION,
                "exported_at": _now(),
                "projects": {r["path"]: {k: r[k] for k in r.keys() if k != "path"} for r in rows},
            }

    # ── Resolution ────────────────────────────────────────────

    def resolve(self, name_or_path: str | None) -> Project:
        """Resolve a path or registered name to a Project."""
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
                f"工程 {entry['name']} 的路径已失效: {root}"
                f"（可用 se_prune_projects 清理登记）"
            )

        raise ProjectNotFound(f"未找到工程: {name_or_path}")

    def describe(self) -> list[str]:
        return [e.get("name") or e["path"] for e in self.list(probe=False)]


def _manifest_name(root: Path) -> str | None:
    import frontmatter

    try:
        post = frontmatter.load(root / ".vinw" / "manifest.md")
        return post.metadata.get("name")
    except Exception:
        return None
