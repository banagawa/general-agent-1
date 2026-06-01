from __future__ import annotations

from pathlib import Path

import pytest

from sandbox import mounts


def test_workspace_root_comes_from_explicit_env_not_cwd(monkeypatch, tmp_path) -> None:
    app_root = tmp_path / "app"
    workspace_root = tmp_path / "workspace" / "dev"
    random_cwd = tmp_path / "elsewhere"

    app_root.mkdir()
    (app_root / "main.py").write_text("", encoding="utf-8")
    (app_root / "sandbox").mkdir()
    workspace_root.mkdir(parents=True)
    random_cwd.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace_root))
    monkeypatch.chdir(random_cwd)

    assert mounts.get_app_root() == app_root.resolve()
    assert mounts.get_workspace_root() == workspace_root.resolve()
    assert mounts.get_workspace_root() != Path.cwd().resolve()


def test_workspace_root_defaults_under_app_workspace_when_env_absent(monkeypatch, tmp_path) -> None:
    app_root = tmp_path / "app"
    app_root.mkdir()
    (app_root / "main.py").write_text("", encoding="utf-8")
    (app_root / "sandbox").mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.delenv("AGENT_WORKSPACE_ROOT", raising=False)

    assert mounts.get_workspace_root() == (app_root / "workspace").resolve()


def test_workspace_root_must_not_equal_app_root(monkeypatch, tmp_path) -> None:
    app_root = tmp_path / "app"
    app_root.mkdir()
    (app_root / "main.py").write_text("", encoding="utf-8")
    (app_root / "sandbox").mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(app_root))

    with pytest.raises(RuntimeError, match="refusing to use live app repo as workspace"):
        mounts.get_workspace_root()
