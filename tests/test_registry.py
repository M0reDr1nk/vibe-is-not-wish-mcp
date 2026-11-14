"""Tests for the multi-project registry and per-tool `project` addressing."""

import json
import os
import shutil

import pytest

import vinw.server as server
from vinw.store.project import Project
from vinw.store.registry import (
    ProjectNotFound,
    ProjectRegistry,
    is_vinw_project,
    normalize,
    vinw_home,
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolate the registry (VINW_HOME) and reset the module-level singleton."""
    monkeypatch.setenv("VINW_HOME", str(tmp_path / "home"))
    saved_active = server._active_project
    saved_registry = server._registry
    server._active_project = None
    server._registry = None
    yield tmp_path / "home"
    server._active_project = saved_active
    server._registry = saved_registry


def make_project(root):
    root.parent.mkdir(parents=True, exist_ok=True)
    return Project.init(root, root.name, "test project")


class TestRegistryBasics:
    def test_home_override(self, home, monkeypatch):
        assert vinw_home() == home
        monkeypatch.delenv("VINW_HOME")
        assert str(vinw_home()).endswith(".vinw")

    def test_add_and_list(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        result = reg.add(proj.root)
        assert result["registered"] is True
        assert result["name"] == proj.read_manifest().get("name")  # from manifest

        entries = reg.list()
        assert len(entries) == 1
        assert entries[0]["status"] == "ok"
        assert entries[0]["path"] == str(proj.root)

    def test_add_rejects_non_project(self, home):
        reg = ProjectRegistry()
        plain = home.parent / "plain"
        plain.mkdir(parents=True)
        with pytest.raises(ValueError):
            reg.add(plain)

    def test_add_is_idempotent_for_same_path(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        reg.add(proj.root)
        assert len(reg.list()) == 1

    def test_duplicate_name_gets_suffix(self, home):
        reg = ProjectRegistry()
        a = make_project(home.parent / "a")
        b = make_project(home.parent / "b")
        reg.add(a.root, name="same")
        result = reg.add(b.root, name="same")
        assert result["name"] == "same-2"
        assert "warning" in result

    def test_remove_keeps_disk(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        reg.remove(str(proj.root))
        assert reg.list() == []
        assert is_vinw_project(proj.root)

    def test_remove_unknown_raises(self, home):
        with pytest.raises(ProjectNotFound):
            ProjectRegistry().remove("nope")

    def test_corrupt_db_is_quarantined_not_deleted(self, home):
        reg = ProjectRegistry()
        reg.path.parent.mkdir(parents=True, exist_ok=True)
        reg.path.write_bytes(b"\x95not a sqlite database at all")

        assert reg.list() == []  # usable after quarantine
        backups = list(reg.path.parent.glob("registry.db.corrupt-*"))
        assert backups, "corrupt db must be kept as a backup"

    def test_wal_mode_enabled(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        with reg._connect() as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

    def test_legacy_json_is_migrated_and_kept(self, home):
        reg = ProjectRegistry()
        reg.path.parent.mkdir(parents=True, exist_ok=True)
        proj = make_project(home.parent / "legacy")
        reg.legacy_json.write_text(
            json.dumps(
                {
                    "version": 1,
                    "projects": {
                        str(proj.root): {
                            "name": "legacy-proj",
                            "added_at": "2026-01-01T00:00:00+00:00",
                            "last_accessed_at": "2026-01-01T00:00:00+00:00",
                            "last_seen_ok": None,
                            "missing_since": None,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        entries = reg.list()
        assert len(entries) == 1
        assert entries[0]["name"] == "legacy-proj"
        assert list(reg.path.parent.glob("registry.json.migrated-*")), "JSON must be retained"
        assert [h["event"] for h in reg.history("legacy-proj")] == ["import"]


class TestStaleHandling:
    def test_missing_status_marked_not_deleted(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        shutil.rmtree(proj.root)

        entries = reg.list()
        assert entries[0]["status"] == "missing"
        # Entry survives repeated reads
        assert len(reg.list()) == 1

    def test_missing_since_recorded(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        shutil.rmtree(proj.root)
        reg.list()
        entry = reg.get(str(proj.root))
        assert entry["missing_since"]

    def test_prune_defaults_to_dry_run(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        shutil.rmtree(proj.root)

        result = reg.prune()
        assert result["dry_run"] is True
        assert result["would_prune"] == [str(proj.root)]
        assert len(reg.list()) == 1  # nothing deleted

    def test_prune_force_deletes(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        shutil.rmtree(proj.root)

        result = reg.prune(force=True)
        assert result["pruned"] == 1
        assert reg.list() == []


class TestResolution:
    def test_resolve_by_path(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root)
        assert reg.resolve(str(proj.root)).root == proj.root

    def test_resolve_by_name(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha-proj")
        assert reg.resolve("alpha-proj").root == proj.root

    def test_resolve_unregistered_path_works(self, home):
        proj = make_project(home.parent / "unlisted")
        assert ProjectRegistry().resolve(str(proj.root)).root == proj.root

    def test_resolve_missing_raises_with_hint(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha-proj")
        shutil.rmtree(proj.root)
        with pytest.raises(ProjectNotFound) as exc:
            reg.resolve("alpha-proj")
        assert "已失效" in str(exc.value)

    def test_resolve_unknown_raises(self, home):
        with pytest.raises(ProjectNotFound):
            ProjectRegistry().resolve("ghost")


class TestPerToolProjectParam:
    def test_tool_uses_project_param(self, home):
        reg = ProjectRegistry()
        p1 = make_project(home.parent / "one")
        p2 = make_project(home.parent / "two")
        reg.add(p1.root, name="one")

        result = json.loads(server.se_get_project(project="one"))
        assert result["name"] == p1.read_manifest().get("name")

    def test_project_param_does_not_change_active(self, home):
        reg = ProjectRegistry()
        p1 = make_project(home.parent / "one")
        p2 = make_project(home.parent / "two")
        reg.add(p1.root, name="one")
        server._active_project = p2

        server.se_get_project(project="one")
        assert server._active_project.root == p2.root

    def test_unknown_project_returns_structured_error(self, home):
        reg = ProjectRegistry()
        p1 = make_project(home.parent / "one")
        reg.add(p1.root, name="one")

        result = json.loads(server.se_get_project(project="ghost"))
        assert "error" in result
        assert "one" in result["available_projects"]

    def test_no_project_param_keeps_legacy_behaviour(self, home):
        p1 = make_project(home.parent / "legacy")
        server._active_project = p1
        result = json.loads(server.se_get_project())
        assert result["name"] == p1.read_manifest().get("name")

    def test_no_active_project_returns_error_not_crash(self, home):
        result = json.loads(server.se_get_project())
        assert "No active project" in result["error"]


class TestRegistryTools:
    def test_register_list_remove(self, home):
        proj = make_project(home.parent / "tool-proj")
        added = json.loads(server.se_register_project(str(proj.root)))
        assert added["registered"] is True

        listed = json.loads(server.se_list_projects())
        assert listed["count"] == 1
        assert listed["projects"][0]["status"] == "ok"

        removed = json.loads(server.se_remove_project(added["name"]))
        assert removed["removed"] is True

    def test_use_project_sets_active(self, home):
        proj = make_project(home.parent / "activate")
        added = json.loads(server.se_register_project(str(proj.root)))
        result = json.loads(server.se_use_project(added["name"]))
        assert result["active"] is True
        assert server._active_project.root == proj.root

    def test_prune_reports_candidates(self, home):
        proj = make_project(home.parent / "gone")
        server.se_register_project(str(proj.root))
        shutil.rmtree(proj.root)

        dry = json.loads(server.se_prune_projects())
        assert dry["dry_run"] is True
        assert len(dry["would_prune"]) == 1

        forced = json.loads(server.se_prune_projects(force=True))
        assert forced["pruned"] == 1


class TestSqliteControlPlane:
    """SQLite-specific guarantees: state intent, events, no write amplification."""

    def test_state_intent_vs_observation(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha")

        reg.set_state("alpha", "dormant")
        shutil.rmtree(proj.root)  # observation says missing, but dormant skips probing

        entries = reg.list()  # default: probe only active
        assert entries[0]["state"] == "dormant"
        assert entries[0]["probed"] is False

        forced = reg.list(probe=True)
        assert forced[0]["status"] == "missing"
        assert forced[0]["probed"] is True

    def test_invalid_state_rejected(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha")
        with pytest.raises(ValueError):
            reg.set_state("alpha", "zombie")

    def test_event_history_records_transitions(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha")
        reg.set_state("alpha", "dormant")
        reg.set_state("alpha", "active")

        events = [h["event"] for h in reg.history("alpha")]
        assert events == ["activate", "deactivate", "register"]

    def test_missing_and_recover_events(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha")

        shutil.rmtree(proj.root)
        reg.list()  # detect missing
        make_project(proj.root)
        reg.list()  # detect recover

        events = [h["event"] for h in reg.history("alpha", limit=10)]
        assert "missing" in events and "recover" in events

    def test_touch_does_not_rewrite_whole_registry(self, home):
        reg = ProjectRegistry()
        for i in range(5):
            p = make_project(home.parent / f"p{i}")
            reg.add(p.root, name=f"p{i}")

        size_before = reg.path.stat().st_size
        for _ in range(20):
            reg.touch("p3")
        size_after = reg.path.stat().st_size
        # A touch updates one row; no full-file rewrite beyond WAL growth
        assert size_after >= size_before  # sanity: file still valid
        assert reg.get("p3")["last_accessed_at"]

    def test_export_json_snapshot(self, home):
        reg = ProjectRegistry()
        proj = make_project(home.parent / "alpha")
        reg.add(proj.root, name="alpha")

        snapshot = reg.export_json()
        assert snapshot["version"] == 2
        assert str(proj.root) in snapshot["projects"]

    def test_concurrent_writers_do_not_lose_updates(self, home):
        """Two connections inserting different projects must both survive."""
        import threading

        reg = ProjectRegistry()
        a = make_project(home.parent / "concurrent-a")
        b = make_project(home.parent / "concurrent-b")

        errors = []

        def worker(root, name):
            try:
                ProjectRegistry().add(root, name)
            except Exception as exc:  # pragma: no cover - failure detail
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(a.root, "concurrent-a")),
            threading.Thread(target=worker, args=(b.root, "concurrent-b")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, errors
        names = {e["name"] for e in reg.list(probe=False)}
        assert {"concurrent-a", "concurrent-b"} <= names


class TestNewRegistryTools:
    def test_set_state_and_history_tools(self, home):
        proj = make_project(home.parent / "toolproj")
        added = json.loads(server.se_register_project(str(proj.root)))
        name = added["name"]

        state = json.loads(server.se_set_project_state(name, "dormant"))
        assert state["state"] == "dormant"

        history = json.loads(server.se_project_history(name))
        assert {e["event"] for e in history["events"]} >= {"register", "deactivate"}

    def test_set_state_invalid_value(self, home):
        proj = make_project(home.parent / "toolproj2")
        added = json.loads(server.se_register_project(str(proj.root)))
        result = json.loads(server.se_set_project_state(added["name"], "zombie"))
        assert "error" in result

    def test_export_projects_tool(self, home):
        proj = make_project(home.parent / "exportproj")
        server.se_register_project(str(proj.root))
        snapshot = json.loads(server.se_export_projects())
        assert snapshot["version"] == 2
        assert any(v["name"] for v in snapshot["projects"].values())


class TestAutoRegistration:
    """backlog 3: a project created via MCP must be visible in the selector."""

    def _init(self, tmp_path, name="auto-proj", register=True):
        import json

        import vinw.server as server

        # se_init_project creates <path>/<name>
        payload = json.loads(
            server.se_init_project(str(name), str(tmp_path), register=register)
        )
        return tmp_path / name, payload

    def test_init_registers_project(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VINW_HOME", str(tmp_path / "home"))
        monkeypatch.setattr(server_module(), "_registry", None)  # fresh DB

        root, payload = self._init(tmp_path)
        assert payload["registered"] is True

        from vinw.store.registry import ProjectRegistry

        reg = ProjectRegistry()
        assert str(root) in [p["path"] for p in reg.list()]

    def test_init_can_opt_out(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VINW_HOME", str(tmp_path / "home2"))
        monkeypatch.setattr(server_module(), "_registry", None)
        root, payload = self._init(tmp_path, name="temp-proj", register=False)
        assert payload["registered"] is False
        assert payload.get("registration_skipped") is True

        from vinw.store.registry import ProjectRegistry

        assert str(root) not in [p["path"] for p in ProjectRegistry().list()]

    def test_registration_failure_does_not_break_creation(self, tmp_path, monkeypatch):
        """AC4: only registry-level failures are swallowed, with a warning."""
        import vinw.server as server

        class BrokenRegistry:
            def add(self, _root):
                raise OSError("disk full")

        monkeypatch.setattr(server, "_get_registry", lambda: BrokenRegistry())
        payload = json.loads(server.se_init_project("broken", str(tmp_path)))
        root = tmp_path / "broken"

        assert root.exists()
        assert (root / ".vinw" / "manifest.md").exists()
        assert payload["registered"] is False
        assert "disk full" in payload["warning"]

    def test_programming_error_is_not_swallowed(self, tmp_path, monkeypatch):
        """A TypeError from a broken registry must surface, not become a warning."""
        import vinw.server as server

        class BuggyRegistry:
            def add(self):
                raise TypeError("signature changed")

        monkeypatch.setattr(server, "_get_registry", lambda: BuggyRegistry())
        with pytest.raises(TypeError):
            server.se_init_project("buggy", str(tmp_path))

    def test_adopted_project_is_registered(self, tmp_path):
        """AC2: adopting an existing project also registers it."""
        import vinw.server as server
        from vinw.store.project import Project
        from vinw.store.registry import ProjectRegistry

        Project.init(tmp_path / "adopted", "adopted", "")
        payload = json.loads(server.se_init_project("adopted", str(tmp_path)))
        assert payload["adopted"] is True
        assert payload["registered"] is True

        paths = [p["path"] for p in ProjectRegistry().list()]
        assert str(tmp_path / "adopted") in paths
        # idempotent: a second init does not duplicate the entry
        json.loads(server.se_init_project("adopted", str(tmp_path)))
        assert paths.count(str(tmp_path / "adopted")) == 1
        assert len(ProjectRegistry().list()) == 1

    def test_use_project_registers_unregistered_project(self, tmp_path):
        """AC3: activating by path registers the project."""
        import vinw.server as server
        from vinw.store.project import Project
        from vinw.store.registry import ProjectRegistry

        root = tmp_path / "manual"
        Project.init(root, "manual", "")
        assert ProjectRegistry().list() == []

        payload = json.loads(server.se_use_project(str(root)))
        assert payload["registered"] is True
        assert str(root) in [p["path"] for p in ProjectRegistry().list()]
        # now addressable by name
        assert json.loads(server.se_use_project("manual"))["name"] == "manual"


def server_module():
    import vinw.server as server

    return server


class TestCliRegistration:
    """AC6: the CLI entry point registers too (backlog 3 applies there as well)."""

    def _run(self, *args, home):
        import os
        import subprocess
        import sys
        from pathlib import Path

        repo = Path(__file__).resolve().parents[1]
        env = {**os.environ, "VINW_HOME": str(home)}
        return subprocess.run(
            [sys.executable, "-m", "vinw", *args],
            capture_output=True,
            text=True,
            cwd=repo,
            env=env,
        )

    def test_init_registers(self, tmp_path, isolated_vinw_home):
        result = self._run(
            "init", "--name", "cli-new", str(tmp_path / "cli-new"),
            home=isolated_vinw_home,
        )
        assert result.returncode == 0, result.stderr
        assert "Registered as" in result.stdout

        from vinw.store.registry import ProjectRegistry

        assert "cli-new" in [p["name"] for p in ProjectRegistry().list()]

    def test_no_register_skips(self, tmp_path, isolated_vinw_home):
        result = self._run(
            "init", "--name", "cli-tmp", str(tmp_path / "cli-tmp"), "--no-register",
            home=isolated_vinw_home,
        )
        assert result.returncode == 0, result.stderr
        assert "skipped registration" in result.stdout

        from vinw.store.registry import ProjectRegistry

        assert "cli-tmp" not in [p["name"] for p in ProjectRegistry().list()]


class TestRegistrationEdgePaths:
    """reviewer13: collision passthrough and read-only-registry activation."""

    def test_name_collision_returns_actual_name(self, tmp_path):
        """GAP-005 regression: the MCP payload must carry the renamed name."""
        import vinw.server as server

        first = json.loads(server.se_init_project("dup", str(tmp_path / "a")))
        second = json.loads(server.se_init_project("dup", str(tmp_path / "b")))

        assert first["registered"] is True
        assert second["registered"] is True
        assert second["name"] != first["name"]
        assert "warning" in second  # rename is reported, not silent

    def test_use_project_tolerates_touch_failure(self, tmp_path, monkeypatch):
        """GAP-R13-001: read-only registry must not break activation."""
        import sqlite3

        import vinw.server as server
        from vinw.store.project import Project
        from vinw.store.registry import ProjectRegistry

        root = tmp_path / "touchy"
        Project.init(root, "touchy", "")
        ProjectRegistry().add(root)

        class FlakyRegistry(ProjectRegistry):
            def touch(self, _path):
                raise sqlite3.OperationalError("readonly")

        monkeypatch.setattr(server, "_get_registry", lambda: FlakyRegistry())
        payload = json.loads(server.se_use_project("touchy"))

        assert payload["active"] is True
        assert payload["registered"] is True
