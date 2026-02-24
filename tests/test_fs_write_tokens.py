from __future__ import annotations

from pathlib import Path
import pytest

from policy.capabilities import issue_token
from tools.gateway import ToolGateway
from sandbox.mounts import get_workspace_root


@pytest.fixture()
def workspace_sandbox(tmp_path: Path) -> Path:
    """
    Create a temp directory *inside* the real workspace root so PolicyEngine allows FS_WRITE_PATCH.
    """
    ws = Path(get_workspace_root()).resolve()
    d = ws / "_pytest_fs_write_tokens" / tmp_path.name
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_gateway_write_requires_token(workspace_sandbox: Path):
    p = (workspace_sandbox / "file.txt").resolve()
    p.write_text("old", encoding="utf-8")

    gw = ToolGateway()

    # no token => deny (capability layer)
    with pytest.raises(PermissionError):
        gw.write_file(p, "new", cap_token_id=None)

    # valid token scoped to path => token layer allows AND policy should allow because path is under workspace root
    tok = issue_token(actions=["FS_WRITE_PATCH"], scope={"path": str(p)}, ttl_seconds=60)
    diff = gw.write_file(p, "new", cap_token_id=tok.id)

    assert diff
    assert p.read_text(encoding="utf-8") == "new"
