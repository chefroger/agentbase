"""开发者端点：API 文档、结构化端点清单、静态目录覆盖。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _build_app() -> FastAPI:
    from agentbase.api import deps, router as api_router
    from agentbase.app import _create_system_router

    deps.set_session_token("test-token")
    app = FastAPI()
    app.include_router(_create_system_router(), prefix="/api/agentbase")
    app.include_router(api_router, prefix="/api/agentbase")
    return app


@pytest.fixture
def client():
    return TestClient(_build_app())


class TestApiDocs:
    def test_docs_file_exists_and_covers_routes(self):
        root = Path(__file__).resolve().parent.parent
        docs = (root / "docs" / "API.md").read_text(encoding="utf-8")

        from agentbase.api import router as api_router

        missing = []
        for route in api_router.routes:
            path = getattr(route, "path", "")
            if not path or path.startswith("/openapi") or path.startswith("/docs"):
                continue
            expected = "/api/agentbase" + path
            if expected not in docs:
                missing.append(expected)
        assert not missing, f"docs/API.md 缺少路由：{missing}"

        for system_path in (
            "/api/agentbase/system/service-status",
            "/api/agentbase/system/autostart",
            "/api/agentbase/system/quit",
            "/api/agentbase/system/update",
            "/api/agentbase/system/logs",
            "/api/agentbase/meta/endpoints",
            "/api/agentbase/meta/api-docs",
        ):
            assert system_path in docs, f"docs/API.md 缺少 {system_path}"

    def test_meta_docs_endpoint(self, client):
        r = client.get(
            "/api/agentbase/meta/api-docs",
            headers={"X-Hermes-Session-Token": "test-token"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["format"] == "markdown"
        assert "AgentBase API" in data["content"]
        assert data["openapi_url"] == "/openapi.json"

    def test_meta_docs_override(self, tmp_path, monkeypatch):
        from agentbase.api.meta import get_api_docs

        (tmp_path / "API.md").write_text("# custom docs", encoding="utf-8")
        monkeypatch.setenv("AGENTBASE_DOCS_DIR", str(tmp_path))
        assert get_api_docs()["content"] == "# custom docs"

    def test_meta_docs_missing_returns_404(self, tmp_path, monkeypatch):
        from agentbase.api.meta import get_api_docs

        monkeypatch.setenv("AGENTBASE_DOCS_DIR", str(tmp_path / "nope"))
        monkeypatch.setattr("agentbase.api.meta.resolve_api_docs_path", lambda: None)
        with pytest.raises(HTTPException) as exc:
            get_api_docs()
        assert exc.value.status_code == 404


class TestEndpointCatalog:
    def test_catalog_marks_auth(self, client):
        r = client.get(
            "/api/agentbase/meta/endpoints",
            headers={"X-Hermes-Session-Token": "test-token"},
        )
        assert r.status_code == 200
        endpoints = {(e["method"], e["path"]): e for e in r.json()["endpoints"]}

        assert ("POST", "/api/agentbase/chat/stream") in endpoints
        chat = endpoints[("POST", "/api/agentbase/chat/stream")]
        assert chat["requires_token"] is True
        assert chat["requires_workspace"] is True

        settings = endpoints[("GET", "/api/agentbase/settings")]
        assert settings["requires_token"] is True
        assert settings["requires_workspace"] is False

        for method, path in endpoints:
            assert not path.startswith("/static")
            assert path not in ("/openapi.json", "/docs")

    def test_catalog_includes_business_and_meta(self, client):
        r = client.get(
            "/api/agentbase/meta/endpoints",
            headers={"X-Hermes-Session-Token": "test-token"},
        )
        paths = {e["path"] for e in r.json()["endpoints"]}
        assert "/api/agentbase/business/config" in paths
        assert "/api/agentbase/meta/endpoints" in paths
        assert "/api/agentbase/system/logs" in paths


class TestStaticDirOverride:
    def test_override_wins(self, tmp_path, monkeypatch):
        from agentbase.app import _resolve_static_dir

        monkeypatch.setenv("AGENTBASE_STATIC_DIR", str(tmp_path))
        assert _resolve_static_dir() == tmp_path.resolve()

    def test_falls_back_to_repo_static(self, tmp_path, monkeypatch):
        from agentbase.app import _resolve_static_dir

        monkeypatch.delenv("AGENTBASE_STATIC_DIR", raising=False)
        monkeypatch.setenv("AGENT_HOME", str(tmp_path))
        resolved = _resolve_static_dir()
        assert resolved.name == "static"
        assert (resolved / "app.html").is_file()
