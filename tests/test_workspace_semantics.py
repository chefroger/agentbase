"""workspace 机制/语义分离：默认创建策略、自定义字段、身份文件同步。"""

from __future__ import annotations

import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    import agentbase.database as db

    db.init_db()
    from agentbase import business_config

    business_config.reload()
    return tmp_path


def _write_business(home, text: str):
    (home / "business.yaml").write_text(text, encoding="utf-8")
    from agentbase import business_config

    business_config.reload()


class TestDefaultWorkspacePolicy:
    def test_single_create_default(self, home):
        from agentbase.workspace import ensure_default_workspace

        assert ensure_default_workspace() is not None

    def test_multi_mode_does_not_auto_create(self, home):
        _write_business(home, "workspaces:\n  mode: multi\n  create_default: true\n")
        from agentbase.workspace import ensure_default_workspace

        assert ensure_default_workspace() is None

    def test_create_default_false_does_not_auto_create(self, home):
        _write_business(home, "workspaces:\n  mode: single\n  create_default: false\n")
        from agentbase.workspace import ensure_default_workspace

        assert ensure_default_workspace() is None

    def test_defaults_remain_backward_compatible(self, home):
        from agentbase import business_config

        cfg = business_config.workspaces_config()
        assert cfg["mode"] == "single"
        assert cfg["create_default"] is True
        assert cfg["term"] == "工作区"


class TestCustomFields:
    def test_create_roundtrip(self, home):
        from agentbase import workspace

        ws = workspace.create(name="项目A", custom_fields={"project_code": "P-1"})
        assert ws["custom_fields"] == {"project_code": "P-1"}
        assert workspace.get(ws["id"])["custom_fields"] == {"project_code": "P-1"}

    def test_update_replaces_fields(self, home):
        from agentbase import workspace

        ws = workspace.create(name="项目B", custom_fields={"project_code": "P-1"})
        updated = workspace.update(ws["id"], custom_fields={"project_code": "P-2"})
        assert updated["custom_fields"] == {"project_code": "P-2"}

    def test_list_includes_fields(self, home):
        from agentbase import workspace

        workspace.create(name="项目C", custom_fields={"project_code": "P-3"})
        rows = workspace.list_all()
        assert rows[0]["custom_fields"] == {"project_code": "P-3"}

    def test_missing_extra_is_empty(self, home):
        from agentbase import workspace

        ws = workspace.create(name="项目D")
        assert ws["custom_fields"] == {}


class TestAgentIdentityFileSync:
    def test_api_update_writes_identity_file(self, home):
        """提示词解析是文件优先：PUT 必须同时写 DB 与 identity 文件。"""
        from agentbase import workspace
        from agentbase.api.models import AgentIdentityUpdate
        from agentbase.api.workspaces import update_workspace_agent_identity
        from agentbase.prompts import get_agent_identity_by_slug

        ws = workspace.create(name="身份同步")
        update_workspace_agent_identity(
            ws["id"],
            AgentIdentityUpdate(agent_identity_md="# 新身份\n\n- 角色：测试"),
            x_workspace_id=ws["id"],
        )

        content = get_agent_identity_by_slug(ws["slug"])
        assert "# 新身份" in content
        assert "角色：测试" in content
