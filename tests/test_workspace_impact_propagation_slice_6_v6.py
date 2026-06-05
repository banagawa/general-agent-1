import pytest

from agent_core.workspace_graph import build_workspace_graph, impacted_tests_for_functions


def test_impacted_tests_for_functions_selects_direct_test_callers(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text("def format_output():\n    return 'ok'\n", encoding="utf-8")
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import format_output\n\ndef test_format_output():\n    assert format_output() == 'ok'\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_functions(graph, ["FUNC::agent_core/helper.py::format_output"]) == (
        "TEST::tests/test_helper.py::test_format_output",
    )


def test_impacted_tests_for_functions_propagates_through_same_file_callers(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text(
        "def leaf():\n    return 1\n\ndef middle():\n    return leaf()\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import middle\n\ndef test_middle():\n    assert middle() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_functions(graph, ["FUNC::agent_core/helper.py::leaf"]) == (
        "TEST::tests/test_helper.py::test_middle",
    )


def test_impacted_tests_for_functions_propagates_across_imported_callers(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text("def leaf():\n    return 1\n", encoding="utf-8")
    (repo / "agent_core" / "service.py").write_text(
        "from agent_core.helper import leaf\n\ndef middle():\n    return leaf()\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_service.py").write_text(
        "from agent_core.service import middle\n\ndef test_middle():\n    assert middle() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_functions(graph, ["FUNC::agent_core/helper.py::leaf"]) == (
        "TEST::tests/test_service.py::test_middle",
    )


def test_impacted_tests_for_functions_handles_multiple_callers_deterministically(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text(
        "def leaf():\n    return 1\n\ndef first():\n    return leaf()\n\ndef second():\n    return leaf()\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import first, second\n\ndef test_first():\n    assert first() == 1\n\ndef test_second():\n    assert second() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_functions(graph, ["FUNC::agent_core/helper.py::leaf"]) == (
        "TEST::tests/test_helper.py::test_first",
        "TEST::tests/test_helper.py::test_second",
    )


def test_impacted_tests_for_functions_returns_empty_for_unknown_valid_function(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    assert impacted_tests_for_functions(graph, ["FUNC::agent_core/missing.py::run"]) == ()


@pytest.mark.parametrize(
    "artifact_id",
    [
        "FILE::agent_core/helper.py",
        "MODULE::agent_core/helper.py",
        "FUNC::../helper.py::run",
        "FUNC::agent_core/helper.py",
    ],
)
def test_impacted_tests_for_functions_rejects_non_function_or_unsafe_artifacts(tmp_path, artifact_id):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    with pytest.raises(ValueError):
        impacted_tests_for_functions(graph, [artifact_id])


def test_impacted_tests_for_functions_is_read_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    sample = repo / "agent_core" / "helper.py"
    sample.write_text("def leaf():\n    return 1\n\ndef middle():\n    return leaf()\n", encoding="utf-8")
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import middle\n\ndef test_middle():\n    assert middle() == 1\n",
        encoding="utf-8",
    )
    graph = build_workspace_graph(repo)
    before = sample.read_text(encoding="utf-8")

    assert impacted_tests_for_functions(graph, ["FUNC::agent_core/helper.py::leaf"]) == (
        "TEST::tests/test_helper.py::test_middle",
    )
    assert sample.read_text(encoding="utf-8") == before
