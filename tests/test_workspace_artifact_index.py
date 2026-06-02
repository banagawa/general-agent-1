import pytest

from agent_core.workspace_graph import build_workspace_graph


def test_workspace_graph_finds_file_module_function_and_test_artifacts(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "sample.py").write_text(
        "def run():\n    return 1\n\ndef helper():\n    return 2\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_sample.py").write_text(
        "from agent_core.sample import run\n\ndef test_run():\n    assert run() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert graph.find_artifact("FILE::agent_core/sample.py") == {
        "artifact_id": "FILE::agent_core/sample.py",
        "kind": "FILE",
        "path": "agent_core/sample.py",
        "symbol": None,
        "file_artifact_id": "FILE::agent_core/sample.py",
        "module_id": "MODULE::agent_core/sample.py",
        "parse_error": None,
    }
    assert graph.find_artifact("MODULE::agent_core/sample.py")["module_id"] == "MODULE::agent_core/sample.py"
    assert graph.find_artifact("FUNC::agent_core/sample.py::run")["symbol"] == "run"
    assert graph.find_artifact("TEST::tests/test_sample.py::test_run")["kind"] == "TEST"


def test_workspace_graph_find_artifact_returns_none_for_unknown_valid_artifact(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    assert graph.find_artifact("FILE::agent_core/missing.py") is None
    assert graph.find_artifact("FUNC::agent_core/missing.py::run") is None


def test_workspace_graph_find_artifact_rejects_malformed_artifact_ids(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    with pytest.raises(ValueError):
        graph.find_artifact("FILE::../outside.py")

    with pytest.raises(ValueError):
        graph.find_artifact("FUNC::agent_core/sample.py")


def test_workspace_graph_find_artifact_is_read_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    sample = repo / "agent_core" / "sample.py"
    sample.write_text("def run():\n    return 1\n", encoding="utf-8")
    graph = build_workspace_graph(repo)
    before = sample.read_text(encoding="utf-8")

    assert graph.find_artifact("FUNC::agent_core/sample.py::run") is not None

    after = sample.read_text(encoding="utf-8")
    assert after == before
