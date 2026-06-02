from pathlib import Path

import pytest

from agent_core.artifact_id import ArtifactID, resolve_artifact_path


def test_artifact_id_round_trips_file_and_symbol_ids():
    assert str(ArtifactID.parse("FILE::agent_core/loop.py")) == "FILE::agent_core/loop.py"
    assert str(ArtifactID.parse("MODULE::agent_core/loop.py")) == "MODULE::agent_core/loop.py"
    assert str(ArtifactID.parse("FUNC::agent_core/loop.py::run")) == "FUNC::agent_core/loop.py::run"
    assert str(ArtifactID.parse("TEST::tests/test_smoke.py::test_import")) == "TEST::tests/test_smoke.py::test_import"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "UNKNOWN::agent_core/loop.py",
        "FILE::../agent_core/loop.py",
        "FILE::/tmp/x.py",
        "FILE::C:/tmp/x.py",
        "FILE::agent_core//loop.py",
        "FUNC::agent_core/loop.py",
        "FILE::agent_core/loop.py::run",
        "FUNC::agent_core/loop.py::bad/name",
    ],
)
def test_artifact_id_rejects_invalid_or_unsafe_values(value):
    with pytest.raises(ValueError):
        ArtifactID.parse(value)


def test_resolve_artifact_path_fails_closed_outside_workspace(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    artifact = ArtifactID.parse("FILE::agent_core/loop.py")
    assert resolve_artifact_path(artifact, root) == (root / "agent_core" / "loop.py").resolve()

    with pytest.raises(ValueError):
        resolve_artifact_path("FILE::../outside.py", root)
