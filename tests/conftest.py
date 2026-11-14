"""Global test isolation.

Automatic registration (v0.16) means any test that creates a project would
write to the developer's real registry under ~/.vinw. Every test now gets a
throwaway VINW_HOME and a reset registry/active-project singleton.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_vinw_home(tmp_path, monkeypatch):
    home = tmp_path / "vinw-home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("VINW_HOME", str(home))

    import vinw.server as server

    monkeypatch.setattr(server, "_registry", None, raising=False)
    monkeypatch.setattr(server, "_active_project", None, raising=False)
    yield home
