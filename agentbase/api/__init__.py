"""
Trade AI Assistant — REST API Router。

组装所有子路由模块，对外暴露统一的 router。
所有路由默认受 session token 保护。
server.py 通过 ``from agentbase.api import router`` 挂载到 /api/agentbase。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from agentbase.api.chat import router as chat_router
from agentbase.api.conversations import router as conversations_router
from agentbase.api.cron import router as cron_router
from agentbase.api.deps import opt_workspace, require_session, require_workspace
from agentbase.api.files import router as files_router
from agentbase.api.memory import router as memory_router
from agentbase.api.onboarding import router as onboarding_router
from agentbase.api.packs import router as packs_router
from agentbase.api.settings import router as settings_router
from agentbase.api.workspaces import router as companies_router


def _enforce_workspace_binding(
    request: Request,
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
) -> None:
    """session 级活跃公司绑定：防止修改 header 跨公司越权。

    作为全局 trade router 的依赖，在每个业务请求前自动执行。
    首次携带 workspace_id 的请求自动绑定 session 到该公司；
    后续请求必须携带匹配的 workspace_id。
    """
    from agentbase.api.deps import _ACTIVE_WORKSPACE, _workspace_bind_lock

    token = request.headers.get("X-Hermes-Session-Token", "")
    if not token:
        return  # 无 session token 不检查

    if not x_workspace_id or not x_workspace_id.strip():
        return  # 无 workspace_id 不检查（由 require_workspace 端点自行处理）

    try:
        cid = int(x_workspace_id.strip())
    except ValueError:
        return  # 无效 ID 由 require_workspace 处理

    # switch 端点允许携带不同于当前绑定的 workspace_id（因为它的语义就是切换）
    if "/switch" in request.url.path:
        return

    with _workspace_bind_lock:
        bound = _ACTIVE_WORKSPACE.get(token)
        if bound is not None and cid != bound:
            raise HTTPException(
                status_code=403,
                detail=f"X-Workspace-ID {cid} does not match active session. "
                       f"Use POST /api/agentbase/workspaces/{cid}/switch to switch.",
            )
        if bound is None:
            _ACTIVE_WORKSPACE[token] = cid


# 所有 /api/agentbase/* 路由默认要求 session token + 公司绑定
router = APIRouter(
    tags=["agentbase"],
    dependencies=[Depends(require_session), Depends(_enforce_workspace_binding)],
)

# 框架域子路由（业务 API 由 skill 包自带，不在此挂载）
router.include_router(companies_router)
router.include_router(onboarding_router)
router.include_router(conversations_router)
router.include_router(chat_router)
router.include_router(memory_router)
router.include_router(cron_router)
router.include_router(files_router)
router.include_router(settings_router)
router.include_router(packs_router)

# 便捷导出
__all__ = [
    "router",
    "require_workspace",
    "opt_workspace",
    "require_session",
]
