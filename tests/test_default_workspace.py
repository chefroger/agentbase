"""首启自动创建默认工作区（单业务框架不向用户暴露「公司」概念）。"""

from __future__ import annotations

import pytest


@pytest.fixture
def empty_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    import agentbase.database as db

    db.init_db()
    return tmp_path


class TestEnsureDefaultWorkspace:
    def test_creates_one_when_empty(self, empty_home):
        import agentbase.database as db
        from agentbase.workspace import ensure_default_workspace

        con = db.get_connection()
        count = con.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0]
        assert count == 0, (count, db._get_db_path())

        ws = ensure_default_workspace()

        assert ws is not None, (db._get_db_path(), count)
        assert ws["name"]
        assert ws["is_active"]

    def test_idempotent(self, empty_home):
        from agentbase.workspace import ensure_default_workspace

        assert ensure_default_workspace() is not None
        assert ensure_default_workspace() is None

    def test_does_not_touch_existing_workspace(self, empty_home):
        import agentbase.database as db
        from agentbase.workspace import ensure_default_workspace

        con = db.get_connection()
        con.execute("INSERT INTO workspaces (name, slug, is_active) VALUES ('已有', 'existing', 1)")
        con.commit()

        assert ensure_default_workspace() is None
        row = con.execute("SELECT COUNT(*) FROM workspaces").fetchone()
        assert row[0] == 1

    def test_uses_business_name(self, empty_home):
        from agentbase.workspace import ensure_default_workspace

        (empty_home / "business.yaml").write_text(
            "business_name: 我的业务\nonboarding_fields: []\nwork_dirs: []\n",
            encoding="utf-8",
        )
        # business_config 有缓存，清掉以读到新文件
        from agentbase import business_config

        business_config._CACHE = None
        business_config._CACHE_KEY = None

        ws = ensure_default_workspace()
        assert ws["name"] == "我的业务"
