from agent_core.plan_executor import _rollback_mutations


def test_rollback_refuses_snapshot_outside_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    outside.write_text("outside\n", encoding="utf-8")
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    report = _rollback_mutations(
        "planhash",
        "txid",
        [
            {
                "step_id": 1,
                "tool": "PATCH_APPLY",
                "path": "../outside.txt",
                "absolute_path": str(outside),
                "existed": True,
                "content": "changed\n",
            }
        ],
    )

    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert report["restored_paths"] == []
    assert report["errors"]
