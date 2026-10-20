"""工作区软删除与创建失败补偿。"""

from __future__ import annotations

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
