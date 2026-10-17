"""安全加固回归测试（审计 #11 / #12）。

#11 license 路由：
- POST /license/activate 必须带 session token（写操作）
- GET /license/status 保持免鉴权（登录前展示品牌），且不再接受 workspace 参数

#12 chat-memory 的 workspace_id：
- 由服务端 workspace 上下文绑定，LLM 无法通过工具参数越权
- 绑定值能跨 Hermes 的工具执行线程（contextvars 复制语义）
"""

from __future__ import annotations

import contextvars
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def license_client():
    from agentbase.api import deps
    from agentbase.api import license as license_api

    app = FastAPI()
    app.include_router(license_api.router, prefix="/api/agentbase")
    deps.set_session_token("test-token")
    return TestClient(app), license_api, deps


class TestLicenseRouteAuth:
    def test_activate_requires_session_token(self, license_client, monkeypatch):
        client, license_api, _deps = license_client
        called = []
        monkeypatch.setattr(license_api, "_activate", lambda code: called.append(code) or (True, "ok"))

        r = client.post("/api/agentbase/license/activate", json={"code": "AGENTBASE-x"})

        assert r.status_code == 401
        assert called == [], "未鉴权的请求不应触达激活逻辑"

    def test_activate_rejects_wrong_token(self, license_client, monkeypatch):
        client, license_api, _deps = license_client
        monkeypatch.setattr(license_api, "_activate", lambda code: (True, "ok"))

        r = client.post(
            "/api/agentbase/license/activate",
            json={"code": "AGENTBASE-x"},
            headers={"X-Hermes-Session-Token": "wrong"},
        )

        assert r.status_code == 401

    def test_activate_succeeds_with_session_token(self, license_client, monkeypatch):
        client, license_api, _deps = license_client
        seen = []
        monkeypatch.setattr(license_api, "_activate", lambda code: seen.append(code) or (True, "激活成功"))

        r = client.post(
            "/api/agentbase/license/activate",
            json={"code": "AGENTBASE-x"},
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True, "message": "激活成功"}
        assert seen == ["AGENTBASE-x"]

    def test_status_stays_public(self, license_client, monkeypatch):
        client, license_api, _deps = license_client
        monkeypatch.setattr(license_api, "_status", lambda: {"status": "trial"})

        r = client.get("/api/agentbase/license/status")

        assert r.status_code == 200
        assert r.json() == {"status": "trial"}

    def test_status_ignores_workspace_header(self, license_client, monkeypatch):
        """许可证是机器级的：workspace header 不应改变返回内容。"""
        client, license_api, _deps = license_client
        calls = []

        def fake_status(*args, **kwargs):
            calls.append(kwargs)
            return {"status": "trial"}

        monkeypatch.setattr(license_api, "_status", fake_status)

        r = client.get(
            "/api/agentbase/license/status",
            headers={"X-Workspace-ID": "123"},
        )

        assert r.status_code == 200
        assert calls == [{}], "status 不应接收 workspace_id"


class TestWorkspaceContextTrust:
    def test_unbound_context_is_none(self):
        from agentbase.workspace_context import current_workspace_id

        assert current_workspace_id() is None

    def test_binding_is_scoped(self):
        from agentbase.workspace_context import bind_workspace, current_workspace_id

        with bind_workspace(7):
            assert current_workspace_id() == 7
        assert current_workspace_id() is None

    def test_binding_survives_thread_propagation(self):
        """Hermes 用 contextvars.copy_context() 把上下文带进工具执行线程。

        这里复刻那个复制时刻，确认绑定值在 worker 线程里仍可见 ——
        否则 handler 会 fail-closed，chat_memory_list 在真实调用中不可用。
        """
        from agentbase.workspace_context import bind_workspace, current_workspace_id

        with bind_workspace(42):
            worker_ctx = contextvars.copy_context()

        seen: list[int | None] = []

        def _worker():
            seen.append(worker_ctx.run(current_workspace_id))

        t = threading.Thread(target=_worker)
        t.start()
        t.join()

        assert seen == [42]
