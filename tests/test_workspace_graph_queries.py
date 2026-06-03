import pytest

from agent_core.workspace_graph import build_workspace_graph


def test_workspace_graph_query_helpers_find_file_module_function_and_test(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "sample.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (repo / "tests" / "test_sample.py").write_text(
        "from agent_core.sample import run\n\ndef test_run():\n    assert run() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert graph.find_file("agent_core/sample.py") == {
        "artifact_id": "FILE::agent_core/sample.py",
        "kind": "FILE",
        "path": "agent_core/sample.py",
        "symbol": None,
        "file_artifact_id": "FILE::agent_core/sample.py",
        "module_id": "MODULE::agent_core/sample.py",
        "parse_error": None,
    }
    assert graph.find_module("agent_core/sample.py")["artifact_id"] == "MODULE::agent_core/sample.py"
    assert graph.find_function("agent_core/sample.py", "run")["artifact_id"] == "FUNC::agent_core/sample.py::run"
    assert graph.find_test("tests/test_sample.py", "test_run")["artifact_id"] == "TEST::tests/test_sample.py::test_run"


def test_workspace_graph_query_helpers_return_none_for_unknown_valid_artifacts(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "agent_core" / "sample.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    graph = build_workspace_graph(repo)

    assert graph.find_file("agent_core/missing.py") is None
    assert graph.find_module("agent_core/missing.py") is None
    assert graph.find_function("agent_core/sample.py", "missing") is None
    assert graph.find_test("tests/test_missing.py", "test_missing") is None


@pytest.mark.parametrize(
    "call",
    [
        lambda graph: graph.find_file("../agent_core/sample.py"),
        lambda graph: graph.find_module("/tmp/sample.py"),
        lambda graph: graph.find_function("agent_core/sample.py", "bad/name"),
        lambda graph: graph.find_test("tests/test_sample.py", "bad\\name"),
    ],
)
def test_workspace_graph_query_helpers_reject_unsafe_inputs(tmp_path, call):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    with pytest.raises(ValueError):
        call(graph)


def test_workspace_graph_query_helpers_are_read_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    sample = repo / "agent_core" / "sample.py"
    sample.write_text("def run():\n    return 1\n", encoding="utf-8")
    graph = build_workspace_graph(repo)
    before = sample.read_text(encoding="utf-8")

    assert graph.find_function("agent_core/sample.py", "run") is not None

    after = sample.read_text(encoding="utf-8")
    assert after == before
