"""开发者元信息：API 调试控制台需要的端点清单 + 只读 API 文档。

`/meta/endpoints` 从当前 FastAPI app 的路由表生成，保证控制台与真实路由
不会漂移；`/meta/api-docs` 读取随发行版分发的 `docs/API.md`。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["meta"])

_PUBLIC_PATHS = {
    "/api/status",
    "/agentbase",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/api/agentbase/license/status",
    "/api/agentbase/branding",
}


def _requires_workspace(path: str) -> bool:
    """与后端 require_workspace 依赖对应的路径规则。

    新版 FastAPI 把 include_router 包成 _IncludedRouter（顶层 route 没有
    dependant），无法可靠反射依赖；这里用与路由定义一致的显式规则。
    """
    if path in (
        "/api/agentbase/chat",
        "/api/agentbase/chat/stream",
        "/api/agentbase/upload-files",
        "/api/agentbase/cron/today",
        "/api/agentbase/cron/jobs",
    ):
        return True
    return path.startswith("/api/agentbase/conversations") or path.startswith(
        "/api/agentbase/workspaces/{workspace_id}"
    )


@router.get("/meta/endpoints")
def list_endpoints(request: Request) -> dict:
    """返回可供调试控制台使用的端点清单（不含文档/静态页面）。"""
    spec = request.app.openapi()
    endpoints = []
    for path, operations in (spec.get("paths") or {}).items():
        if path.startswith("/static"):
            continue
        if path in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/agentbase"):
            continue
        for method, operation in operations.items():
            method = str(method).upper()
            # OpenAPI 的 path item 允许携带 path-level `parameters`；
            # 只认 HTTP 方法白名单，避免把它当成假端点。
            if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue
            params = [
                p.get("name")
                for p in (operation.get("parameters") or [])
                if p.get("in") == "path" and p.get("name")
            ]
            endpoints.append({
                "method": method,
                "path": path,
                "summary": str(operation.get("summary") or ""),
                "path_params": sorted(params),
                "has_body": "requestBody" in operation,
                "requires_token": path not in _PUBLIC_PATHS,
                "requires_workspace": _requires_workspace(path),
            })

    # include_in_schema=False 的健康检查端点：控制台也需要能调
    endpoints.append({
        "method": "GET",
        "path": "/api/status",
        "summary": "健康检查 / 版本 / Hermes 可用性",
        "path_params": [],
        "has_body": False,
        "requires_token": False,
        "requires_workspace": False,
    })
    endpoints.sort(key=lambda item: (item["path"], item["method"]))
    return {"ok": True, "endpoints": endpoints}


def resolve_api_docs_path() -> Path | None:
    """按 frozen/运行时/开发目录顺序解析 docs/API.md。"""
    override = os.environ.get("AGENTBASE_DOCS_DIR", "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser() / "API.md")
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "docs" / "API.md")
    agent_home = os.environ.get("AGENT_HOME", "").strip()
    if agent_home:
        candidates.append(Path(agent_home) / "agentbase" / "docs" / "API.md")
        candidates.append(Path(agent_home) / "docs" / "API.md")
    candidates.append(Path(__file__).resolve().parent.parent.parent / "docs" / "API.md")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


@router.get("/meta/api-docs")
def get_api_docs() -> dict:
    """返回 API 参考文档（markdown）。"""
    path = resolve_api_docs_path()
    if path is None:
        raise HTTPException(
            status_code=404,
            detail="API 文档未随当前安装分发（docs/API.md）；可改用 /openapi.json 或 /docs。",
        )
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"读取 API 文档失败：{exc}") from exc
    return {
        "ok": True,
        "format": "markdown",
        "source": str(path),
        "content": content,
        "openapi_url": "/openapi.json",
        "swagger_url": "/docs",
    }
