"""工作区绑定豁免：只认 switch 路由名，不认路径子串。

历史实现 `if "/switch" in request.url.path` 会把任何含该子串的路径都豁免，
将来新增 /switcheroo 之类的端点会悄悄绕过跨工作区绑定校验。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _request(path: str, route_name: str | None) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "path": path,
        "query_string": b"",
        "headers": [
            (b"x-hermes-session-token", b"tok"),
            (b"x-workspace-id", b"2"),
        ],
        "route": None if route_name is None else SimpleNamespace(name=route_name),
    }
    return Request(scope)


def _bind(token: str, workspace_id: int) -> None:
    from agentbase.api.deps import _ACTIVE_WORKSPACE

    _ACTIVE_WORKSPACE[token] = workspace_id


def test_switch_route_name_is_exempt():
    from agentbase.api import _enforce_workspace_binding
    from agentbase.api.workspaces import SWITCH_ROUTE_NAME

    _bind("tok", 1)
    # 不抛异常 = 放行
    _enforce_workspace_binding(
        _request("/api/agentbase/workspaces/2/switch", SWITCH_ROUTE_NAME), "2"
    )


def test_path_substring_does_not_exempt():
    """含 /switch 子串但不是 switch 路由 → 仍要做绑定校验。"""
    from agentbase.api import _enforce_workspace_binding

    _bind("tok", 1)
    for path in (
        "/api/agentbase/workspaces/2/switcheroo",
        "/api/agentbase/switchboard/2",
        "/api/agentbase/workspaces/2/switch/extra",
    ):
        with pytest.raises(HTTPException) as exc:
            _enforce_workspace_binding(_request(path, "some_other_route"), "2")
        assert exc.value.status_code == 403, f"{path} 被错误豁免"


def test_missing_route_metadata_fails_closed():
    """拿不到路由信息时按「不豁免」处理，不能 fail-open。"""
    from agentbase.api import _enforce_workspace_binding

    _bind("tok", 1)
    with pytest.raises(HTTPException) as exc:
        _enforce_workspace_binding(
            _request("/api/agentbase/workspaces/2/switch", None), "2"
        )
    assert exc.value.status_code == 403


def test_real_switch_route_name_is_pinned():
    from agentbase.api.workspaces import SWITCH_ROUTE_NAME, router as ws_router

    routes = [
        r for r in ws_router.routes if getattr(r, "path", "").endswith("/switch")
    ]
    assert len(routes) == 1
    assert routes[0].name == SWITCH_ROUTE_NAME


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from agentbase.api import router as api_router
    from agentbase.api.deps import set_session_token

    set_session_token("test-token")
    app = FastAPI()
    app.include_router(api_router, prefix="/api/agentbase")
    return TestClient(app)


def test_real_switch_endpoint_reaches_handler(monkeypatch):
    """真 switch 端点在绑定层被放行：进入 handler 后才报 404（工作区不存在）。"""
    from agentbase.api import workspaces as ws_api

    monkeypatch.setattr(
        ws_api.workspace_module, "get_workspace_record", lambda cid: None
    )
    _bind("test-token", 1)

    r = _client().post(
        "/api/agentbase/workspaces/2/switch",
        headers={
            "X-Hermes-Session-Token": "test-token",
            "X-Workspace-ID": "2",
        },
    )

    assert r.status_code == 404, f"switch 被绑定层拦截：{r.status_code} {r.text}"


def test_non_switch_endpoint_still_enforces_binding():
    _bind("test-token", 1)

    r = _client().get(
        "/api/agentbase/workspaces",
        headers={
            "X-Hermes-Session-Token": "test-token",
            "X-Workspace-ID": "2",
        },
    )

    assert r.status_code == 403
