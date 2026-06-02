from agent_core.workspace_graph import build_workspace_graph, impacted_tests_for_modules


def test_impacted_tests_for_modules_selects_tests_that_import_changed_module(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "sample.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (repo / "tests" / "test_sample.py").write_text(
        "from agent_core.sample import run\n\ndef test_run():\n    assert run() == 1\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_other.py").write_text("def test_other():\n    assert True\n", encoding="utf-8")

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_modules(graph, ["agent_core/sample.py"]) == (
        "TEST::tests/test_sample.py::test_run",
    )


def test_impacted_tests_for_modules_includes_changed_test_file_tests(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "test_changed.py").write_text("def test_changed():\n    assert True\n", encoding="utf-8")

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_modules(graph, ["tests/test_changed.py"]) == (
        "TEST::tests/test_changed.py::test_changed",
    )


def test_impacted_tests_for_modules_ignores_non_python_changed_paths(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "test_docs.py").write_text("def test_docs():\n    assert True\n", encoding="utf-8")

    graph = build_workspace_graph(repo)

    assert impacted_tests_for_modules(graph, ["README.md"]) == ()


def test_impacted_tests_for_modules_rejects_unsafe_changed_paths(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    graph = build_workspace_graph(repo)

    try:
        impacted_tests_for_modules(graph, ["../agent_core/sample.py"])
    except ValueError as exc:
        assert "changed path" in str(exc)
    else:
        raise AssertionError("expected unsafe changed path to fail closed")
