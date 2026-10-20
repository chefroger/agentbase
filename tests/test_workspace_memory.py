"""工作区记忆必须按 workspace 隔离，不能再写全局 MEMORY.md。"""

from __future__ import annotations

import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    import agentbase.workspace.crud as crud
    from agentbase.database import init_db

    monkeypatch.setattr(crud, "AGENT_HOME", tmp_path)
    init_db()
    return tmp_path


def test_memory_is_per_workspace(home):
    from agentbase import helpers
    from agentbase import workspace as ws
    from agentbase.memory import (
        read_workspace_memory,
        retain_to_hermes_memory,
        workspace_memory_path,
    )

    alpha = ws.create(name="Alpha", slug="alpha")
    beta = ws.create(name="Beta", slug="beta")

    assert retain_to_hermes_memory(
        "alpha-q", "alpha-a",
        workspace_id=alpha["id"], workspace_slug="alpha", workspace_name="Alpha",
    )
    assert retain_to_hermes_memory(
        "beta-q", "beta-a",
        workspace_id=beta["id"], workspace_slug="beta", workspace_name="Beta",
    )

    assert "alpha-q" in read_workspace_memory(alpha["id"], "alpha")
    assert "beta-q" not in read_workspace_memory(alpha["id"], "alpha")
    assert workspace_memory_path(alpha["id"], "alpha") != workspace_memory_path(
        beta["id"], "beta"
    )

    # 不再写 Hermes 的全局 MEMORY.md
    assert not (home / "memories" / "MEMORY.md").exists()

    prompt_alpha, _ = helpers.build_query(alpha["id"], "hello")
    prompt_beta, _ = helpers.build_query(beta["id"], "hello")
    assert "alpha-q" in prompt_alpha and "beta-q" not in prompt_alpha
    assert "beta-q" in prompt_beta and "alpha-q" not in prompt_beta


def test_refuses_global_write_without_workspace(home):
    from agentbase.memory import retain_to_hermes_memory

    assert retain_to_hermes_memory("q", "a") is False
    assert not (home / "memories" / "MEMORY.md").exists()
