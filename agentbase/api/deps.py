"""
AgentBase AI Assistant — API 依赖函数。

提供 session token 校验和 workspace_id 解析的共享依赖，
被所有 /api/agentbase/* 路由使用。
"""

from __future__ import annotations

import secrets
import threading

from fastapi import Header, HTTPException, Request

from agentbase import workspace as workspace_module

# ── Session token ────────────────────────────────────────────────────────────

# 由 server.py 在启动时设置
_SESSION_TOKEN: str = ""

# session → 绑定的活跃工作区 ID（单用户场景下防止修改 header 跨工作区越权）
_ACTIVE_WORKSPACE: dict[str, int] = {}
_workspace_bind_lock = threading.Lock()


def set_session_token(token: str) -> None:
    """设置当前会话的 token（server.py 启动时调用）。"""
    global _SESSION_TOKEN
    _SESSION_TOKEN = token


def set_active_workspace(token: str, workspace_id: int) -> None:
    """绑定 session token 到指定工作区（前端切换工作区时调用）。"""
    with _workspace_bind_lock:
        _ACTIVE_WORKSPACE[token] = workspace_id


def require_session(request: Request) -> None:
    """校验 X-Hermes-Session-Token。

    所有 /api/agentbase/* 路由共享此依赖，确保只有持有 token 的
    本机浏览器会话可以访问 API。

    Raises:
        HTTPException(401): token 缺失或不匹配
    """
    token = request.headers.get("X-Hermes-Session-Token", "")
    if not _SESSION_TOKEN:
        # 未初始化（不应发生，防御性编程）
        raise HTTPException(status_code=500, detail="Server not initialized.")
    if not token or not secrets.compare_digest(token, _SESSION_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid or missing session token.")


# ── Workspace ID ────────────────────────────────────────────────────────────────

def require_workspace(
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
) -> int:
    """解析并验证 X-Workspace-ID header，返回 workspace_id。

    session 级别的活跃工作区绑定在路由层通过 _check_workspace_binding() 完成。

    Raises:
        HTTPException(401): header 缺失、无效、或工作区不存在/未激活
    """
    cid_str = x_workspace_id if isinstance(x_workspace_id, str) else ""
    if not cid_str or not cid_str.strip():
        raise HTTPException(
            status_code=401,
            detail="X-Workspace-ID header is required. "
                   "Call GET /api/agentbase/workspaces first to get your workspace IDs.",
        )
    try:
        cid = int(cid_str.strip())
    except ValueError as e:
        raise HTTPException(status_code=401, detail="X-Workspace-ID must be an integer.") from e

    # 验证工作区存在且激活
    tc = workspace_module.get_workspace_record(cid)
    if not tc:
        raise HTTPException(status_code=401, detail=f"Workspace {cid} not found in AgentBase system.")
    if not tc.get("is_active"):
        raise HTTPException(status_code=401, detail=f"Workspace {cid} is inactive.")

    return cid


def opt_workspace(
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
) -> int | None:
    """解析 X-Workspace-ID header，返回 workspace_id 或 None。

    与 require_workspace 的区别：header 缺失时不抛异常。
    仅用于不涉及工作区数据隔离的非敏感端点（如 /memory/status）。

    Raises:
        HTTPException(401): header 存在但无法解析为整数
    """
    if not x_workspace_id or not x_workspace_id.strip():
        return None
    try:
        return int(x_workspace_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=401, detail="X-Workspace-ID must be an integer.") from e
