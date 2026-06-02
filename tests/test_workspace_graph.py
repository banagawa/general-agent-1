from pathlib import Path

from agent_core.workspace_graph import build_workspace_graph, impacted_tests_for_paths


def test_workspace_graph_builds_read_only_python_graph(tmp_path):
    repo = tmp_path / "repo"
    (repo / "agent_core").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "agent_core" / "sample.py").write_text("import os\n\ndef run():\n    return os.name\n", encoding="utf-8")
    (repo / "tests" / "test_sample.py").write_text("from agent_core.sample import run\n\ndef test_run():\n    assert run()\n", encoding="utf-8")
    before = {path.relative_to(repo).as_posix(): path.read_text(encoding="utf-8") for path in repo.rglob("*.py")}

    graph = build_workspace_graph(repo)

    after = {path.relative_to(repo).as_posix(): path.read_text(encoding="utf-8") for path in repo.rglob("*.py")}
    assert before == after
    assert graph.file_count == 2
    assert "FUNC::agent_core/sample.py::run" in graph.files[0].functions
    assert "TEST::tests/test_sample.py::test_run" in graph.files[1].tests
    assert graph.to_dict()["summary"]["test_count"] == 1


def test_workspace_graph_records_parse_errors_without_failing(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "bad.py").write_text("def nope(:\n", encoding="utf-8")

    graph = build_workspace_graph(repo)

    assert graph.file_count == 1
    assert graph.files[0].parse_error.startswith("SyntaxError:")


def test_workspace_graph_audits_rebuild(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.py").write_text("def x():\n    return 1\n", encoding="utf-8")
    events = []

    def fake_log_event(event, meta=None):
        events.append((event, meta))

    monkeypatch.setattr("audit.log.log_event", fake_log_event)

    build_workspace_graph(repo, audit_rebuild=True)

    assert events == [
        (
            "WORKSPACE_GRAPH_REBUILT",
            {
                "workspace_root": str(repo.resolve()),
                "file_count": 1,
                "function_count": 1,
                "test_count": 0,
            },
        )
    ]


def test_impacted_tests_for_paths_selects_only_tests_in_changed_files(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (repo / "tests" / "test_b.py").write_text("def test_b():\n    assert True\n", encoding="utf-8")
    graph = build_workspace_graph(repo)

    assert impacted_tests_for_paths(graph, ["tests/test_b.py"]) == ("TEST::tests/test_b.py::test_b",)
