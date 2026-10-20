"""工作区软删除与创建失败补偿。"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    import agentbase.workspace.crud as crud
    from agentbase.database import init_db

    monkeypatch.setattr(crud, "AGENT_HOME", tmp_path)
    init_db()
    return tmp_path


def test_soft_delete_deactivates_both_tables(home):
    from agentbase import workspace as ws

    w = ws.create(name="Acme", slug="acme")

    assert ws.delete(w["id"]) is True
    assert ws.get(w["id"]) is None
    assert ws.slug_from_id(w["id"]) is None
    assert ws.get_by_slug("acme") is None
    assert ws.get_workspace_record(w["id"])["is_active"] is False


def test_create_failure_keeps_preexisting_data_dir(home, monkeypatch):
    from agentbase import workspace as ws
    import agentbase.workspace.workdir as workdir

    sentinel = home / "acme" / "user-data.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(
        workdir,
        "_setup_work_directory",
        lambda *a, **k: (_ for _ in ()).throw(OSError("desktop unavailable")),
    )

    with pytest.raises(OSError):
        ws.create(name="Acme", slug="acme")
    assert sentinel.is_file(), "历史数据目录被失败补偿误删"


def test_workspace_record_exposes_extra1(home):
    """上传接口要读 extra1.work_dir；记录必须返回该字段。"""
    from agentbase import workspace as ws

    w = ws.create(name="Acme", slug="acme")
    record = ws.get_workspace_record(w["id"])

    assert record["extra1"]
    assert json.loads(record["extra1"])["work_dir"] == w["work_dir"]


def test_identity_file_failure_returns_500_and_keeps_db(home, monkeypatch):
    """identity 文件写失败必须让调用方知道，且不先改 DB。"""
    from fastapi import HTTPException

    from agentbase import prompts
    from agentbase.api import workspaces as api_ws
    from agentbase import workspace as ws

    w = ws.create(name="Acme", slug="acme")

    def _boom(*args, **kwargs):
        raise OSError("readonly")

    monkeypatch.setattr(prompts, "write_agent_identity", _boom)

    class Payload:
        agent_identity_md = "NEW IDENTITY"

    with pytest.raises(HTTPException) as exc:
        api_ws.update_workspace_agent_identity(w["id"], Payload(), w["id"])

    assert exc.value.status_code == 500
    assert ws.get_workspace_record(w["id"])["agent_identity_md"] in (None, "")


def test_create_failure_removes_new_data_dir(home, monkeypatch):
    from agentbase import workspace as ws
    import agentbase.workspace.workdir as workdir

    monkeypatch.setattr(
        workdir,
        "_setup_work_directory",
        lambda *a, **k: (_ for _ in ()).throw(OSError("desktop unavailable")),
    )

    with pytest.raises(OSError):
        ws.create(name="Acme", slug="acme")
    assert not (home / "acme").exists(), "本次新建的数据目录应被清理"
