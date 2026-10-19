"""业务配置 API：方向、workspaces 语义、原子写入。"""

from __future__ import annotations

import yaml

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    from agentbase import business_config

    business_config.reload()

    from agentbase.api.business_config import router

    app = FastAPI()
    app.include_router(router, prefix="/api/agentbase")
    return TestClient(app), tmp_path


class TestBusinessConfigApi:
    def test_malformed_yaml_logs_warning_and_falls_back(self, client, caplog):
        """读路径兜底默认值，但不能静默——坏 YAML 必须留下 warning。"""
        _, home = client
        (home / "business.yaml").write_text(
            'workspaces:\n  term: "公司"\n   mode: [\n', encoding="utf-8"
        )
        from agentbase import business_config

        with caplog.at_level("WARNING", logger="agentbase.business_config"):
            cfg = business_config.reload()

        assert cfg["workspaces"]["term"] == "工作区"
        assert any("语法错误" in record.message for record in caplog.records)

    def test_defaults(self, client):
        api, _ = client
        data = api.get("/api/agentbase/business/config").json()

        assert data["ok"] is True
        assert data["usage_direction"] == "general"
        assert len(data["directions"]) == 4
        assert data["config"]["workspaces"]["mode"] == "single"
        assert data["config"]["workspaces"]["create_default"] is True

    def test_update_direction_and_preserve_unknown_keys(self, client):
        api, home = client
        path = home / "business.yaml"
        path.write_text(
            "business_name: 原名称\ncustom_key: keep-me\nonboarding_fields:\n"
            "  - {key: role, label: 角色, example: x}\n",
            encoding="utf-8",
        )
        from agentbase import business_config

        business_config.reload()

        r = api.put(
            "/api/agentbase/business/config",
            json={
                "usage_direction": "document-analysis",
                "business_name": "新名称",
                "workspaces": {"term": "项目", "mode": "multi", "create_default": False},
            },
        )

        assert r.status_code == 200, r.text
        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert saved["business_name"] == "新名称"
        assert saved["usage_direction"] == "document-analysis"
        assert saved["custom_key"] == "keep-me", "未知顶层键必须保留"
        assert saved["workspaces"]["term"] == "项目"
        assert saved["workspaces"]["mode"] == "multi"
        assert saved["workspaces"]["create_default"] is False

    def test_invalid_direction_rejected(self, client):
        api, _ = client
        r = api.put("/api/agentbase/business/config", json={"usage_direction": "nope"})
        assert r.status_code == 400
        assert "合法值" in r.json()["detail"]

    def test_empty_onboarding_fields_rejected(self, client):
        api, _ = client
        r = api.put("/api/agentbase/business/config", json={"onboarding_fields": []})
        assert r.status_code == 422

    def test_empty_work_dirs_rejected(self, client):
        api, _ = client
        r = api.put("/api/agentbase/business/config", json={"work_dirs": []})
        assert r.status_code == 422

    def test_skill_pack_not_writable_here(self, client):
        api, _ = client
        r = api.put("/api/agentbase/business/config", json={"skill_pack": "x"})
        assert r.status_code == 422

    def test_custom_workspace_fields(self, client):
        api, home = client
        r = api.put(
            "/api/agentbase/business/config",
            json={
                "workspaces": {
                    "fields": [{"key": "project_code", "label": "项目编号", "type": "text"}]
                }
            },
        )
        assert r.status_code == 200, r.text
        saved = yaml.safe_load((home / "business.yaml").read_text(encoding="utf-8"))
        assert saved["workspaces"]["fields"] == [
            {"key": "project_code", "label": "项目编号", "type": "text"}
        ]

    def test_branding_exposes_direction_and_term(self, client):
        api, _ = client
        from agentbase.api.branding import get_branding

        data = get_branding()
        assert data["usage_direction"] == "general"
        assert data["workspaces"]["term"] == "工作区"
        assert data["workspaces"]["mode"] == "single"


class TestWriteUpdates:
    def test_unparseable_file_is_not_overwritten(self, client):
        api, home = client
        path = home / "business.yaml"
        path.write_text(":\n  bad: [", encoding="utf-8")
        original = path.read_text(encoding="utf-8")

        from agentbase import business_config

        with pytest.raises(ValueError):
            business_config.write_updates({"business_name": "x"})
        assert path.read_text(encoding="utf-8") == original
