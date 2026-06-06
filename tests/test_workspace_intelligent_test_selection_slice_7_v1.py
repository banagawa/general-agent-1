import pytest

from agent_core.workspace_graph import build_workspace_graph, select_tests_for_changes


def test_select_tests_for_changes_combines_path_and_function_impacts(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text(
        "def leaf():\n    return 1\n\ndef direct():\n    return 2\n",
        encoding="utf-8",
    )
    (repo / "agent_core" / "service.py").write_text(
        "from agent_core.helper import leaf\n\ndef middle():\n    return leaf()\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import direct\n\ndef test_direct():\n    assert direct() == 2\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_service.py").write_text(
        "from agent_core.service import middle\n\ndef test_middle():\n    assert middle() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    selection = select_tests_for_changes(
        graph,
        changed_paths=["agent_core/helper.py"],
        changed_functions=["FUNC::agent_core/helper.py::leaf"],
    )

    assert selection.tests == (
        "TEST::tests/test_helper.py::test_direct",
        "TEST::tests/test_service.py::test_middle",
    )
    assert selection.run_full_suite is False
    assert selection.reasons == (
        "changed_paths",
        "path_or_module_impacts",
        "changed_functions",
        "function_call_impacts",
    )


def test_select_tests_for_changes_deduplicates_deterministically(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import run\n\ndef test_run():\n    assert run() == 1\n",
        encoding="utf-8",
    )

    graph = build_workspace_graph(repo)

    selection = select_tests_for_changes(
        graph,
        changed_paths=["agent_core/helper.py"],
        changed_functions=["FUNC::agent_core/helper.py::run"],
    )

    assert selection.tests == ("TEST::tests/test_helper.py::test_run",)
    assert selection.run_full_suite is False


def test_select_tests_for_changes_recommends_full_suite_when_no_precise_tests(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "helper.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (repo / "tests" / "test_other.py").write_text("def test_other():\n    assert True\n", encoding="utf-8")

    graph = build_workspace_graph(repo)

    selection = select_tests_for_changes(graph, changed_paths=["README.md"])

    assert selection.tests == ()
    assert selection.run_full_suite is True
    assert selection.reasons == ("changed_paths", "no_precise_tests_selected")


def test_select_tests_for_changes_can_disable_full_suite_fallback(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    selection = select_tests_for_changes(
        graph,
        changed_functions=["FUNC::agent_core/missing.py::run"],
        full_suite_on_no_selection=False,
    )

    assert selection.tests == ()
    assert selection.run_full_suite is False
    assert selection.reasons == ("changed_functions",)


def test_select_tests_for_changes_returns_no_changes_result(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    selection = select_tests_for_changes(graph)

    assert selection.tests == ()
    assert selection.run_full_suite is False
    assert selection.reasons == ("no_changes",)
    assert selection.to_dict() == {
        "tests": [],
        "run_full_suite": False,
        "reasons": ["no_changes"],
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"changed_paths": ["../agent_core/helper.py"]},
        {"changed_functions": ["FILE::agent_core/helper.py"]},
    ],
)
def test_select_tests_for_changes_fails_closed_for_unsafe_inputs(tmp_path, kwargs):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    with pytest.raises(ValueError):
        select_tests_for_changes(graph, **kwargs)


def test_select_tests_for_changes_is_read_only(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    sample = repo / "agent_core" / "helper.py"
    sample.write_text("def run():\n    return 1\n", encoding="utf-8")
    (repo / "tests" / "test_helper.py").write_text(
        "from agent_core.helper import run\n\ndef test_run():\n    assert run() == 1\n",
        encoding="utf-8",
    )
    graph = build_workspace_graph(repo)
    before = sample.read_text(encoding="utf-8")

    selection = select_tests_for_changes(graph, changed_paths=["agent_core/helper.py"])

    assert selection.tests == ("TEST::tests/test_helper.py::test_run",)
    assert sample.read_text(encoding="utf-8") == before
