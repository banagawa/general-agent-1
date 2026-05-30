from pathlib import Path

from policy.capabilities import _scope_allows


def test_path_prefix_requires_real_path_boundary(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    prefix = "foo"
    sibling = "foobar/owned.txt"

    assert _scope_allows({"path_prefix": prefix}, {"path": sibling}) is False


def test_path_prefix_allows_child_path(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    prefix = "foo"
    child = "foo/bar/ok.txt"

    assert _scope_allows({"path_prefix": prefix}, {"path": child}) is True


def test_relative_scope_paths_resolve_under_workspace_not_cwd(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    other_cwd = tmp_path / "other"
    workspace.mkdir()
    other_cwd.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(other_cwd)

    assert _scope_allows({"path_prefix": "src"}, {"path": "src/module.py"}) is True


def test_absolute_scope_outside_workspace_denies(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    assert _scope_allows({"path_prefix": str(outside)}, {"path": str(outside / "x.py")}) is False


def test_unknown_scope_key_denies():
    assert _scope_allows({"future_scope": "anything"}, {"path": "anything"}) is False
