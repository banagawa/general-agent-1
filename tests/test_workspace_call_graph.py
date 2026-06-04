import pytest

from agent_core.workspace_graph import build_workspace_graph


def test_workspace_call_graph_records_same_file_calls(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "agent_core" / "sample.py").write_text(
        "def helper():\n    return 1\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert graph.calls_from("FUNC::agent_core/sample.py::run") == (
        "FUNC::agent_core/sample.py::helper",
    )
    assert graph.called_by("FUNC::agent_core/sample.py::helper") == (
        "FUNC::agent_core/sample.py::run",
    )


def test_workspace_call_graph_records_imported_function_calls(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "agent_core" / "helper.py").write_text(
        "def format_output():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (repo / "agent_core" / "sample.py").write_text(
        "from agent_core.helper import format_output\n\ndef run():\n    return format_output()\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert graph.calls_from("FUNC::agent_core/sample.py::run") == (
        "FUNC::agent_core/helper.py::format_output",
    )
    assert graph.called_by("FUNC::agent_core/helper.py::format_output") == (
        "FUNC::agent_core/sample.py::run",
    )


def test_workspace_call_graph_records_imported_module_attribute_calls(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "agent_core" / "helper.py").write_text(
        "def format_output():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (repo / "agent_core" / "sample.py").write_text(
        "import agent_core.helper as helper\n\ndef run():\n    return helper.format_output()\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert graph.calls_from("FUNC::agent_core/sample.py::run") == (
        "FUNC::agent_core/helper.py::format_output",
    )


def test_workspace_call_graph_returns_empty_for_unknown_valid_functions(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    assert graph.calls_from("FUNC::agent_core/missing.py::run") == ()
    assert graph.called_by("FUNC::agent_core/missing.py::run") == ()


@pytest.mark.parametrize(
    "call",
    [
        lambda graph: graph.calls_from("FILE::agent_core/sample.py"),
        lambda graph: graph.called_by("MODULE::agent_core/sample.py"),
        lambda graph: graph.calls_from("FUNC::../sample.py::run"),
        lambda graph: graph.called_by("FUNC::agent_core/sample.py"),
    ],
)
def test_workspace_call_graph_rejects_non_function_or_unsafe_artifacts(tmp_path, call):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    with pytest.raises(ValueError):
        call(graph)


def test_workspace_call_graph_is_read_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    sample = repo / "agent_core" / "sample.py"
    sample.write_text(
        "def helper():\n    return 1\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    graph = build_workspace_graph(repo)
    before = sample.read_text(encoding="utf-8")

    assert graph.calls_from("FUNC::agent_core/sample.py::run") == (
        "FUNC::agent_core/sample.py::helper",
    )

    after = sample.read_text(encoding="utf-8")
    assert after == before
