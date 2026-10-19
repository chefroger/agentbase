"""
AgentBase AI Assistant — 公司管理 API 路由。

端点：
  GET    /workspaces                          — 列出所有公司
  POST   /workspaces                          — 注册新公司
  GET    /workspaces/{workspace_id}              — 公司详情
  PUT    /workspaces/{workspace_id}              — 更新公司信息
  DELETE /workspaces/{workspace_id}              — 删除公司（级联删除所有数据）
  GET    /workspaces/{workspace_id}/agent-identity   — 获取 Agent 身份
  PUT    /workspaces/{workspace_id}/agent-identity   — 更新 Agent 身份
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from agentbase import workspace as workspace_module
from agentbase.api.deps import require_workspace, set_active_workspace
from agentbase.api.models import (
    AgentIdentityUpdate,
    WorkspaceCreate,
    WorkspaceUpdate,
)

router = APIRouter(tags=["workspaces"])


# ── 公司 CRUD ──────────────────────────────────────────────────────────────

@router.get("/workspaces")
def list_workspaces():
    """列出 AgentBase 系统中所有已注册的公司。"""
    return workspace_module.list_all()


@router.post("/workspaces")
def create_workspace(payload: WorkspaceCreate):
    """注册新公司。slug 省略时自动从 name 生成。自动写入默认 Agent 身份。"""
    try:
        workspace = workspace_module.create(
            name=payload.name, slug=payload.slug,
            logo_url=payload.logo_url, website=payload.website,
            contact_name=payload.contact_name, contact_email=payload.contact_email,
            address=payload.address,
            work_dir_name=payload.work_dir_name,
            custom_fields=payload.custom_fields,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # 自动写入默认 Agent 身份（如果尚未设置）。
    # 不写死行业字段：字段来自 business.yaml，未填写的如实标「未填写」。
    from agentbase.onboarding import _build_agent_identity
    existing = workspace_module.get_agent_identity(workspace["id"])
    if not existing:
        default_identity = _build_agent_identity(workspace["name"], {})
        workspace_module.update_workspace_record(
            workspace_id=workspace["id"],
            agent_identity_md=default_identity,
        )
    return workspace


@router.get("/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: int,
    x_workspace_id: int = Depends(require_workspace),
):
    """根据 ID 获取公司详情。仅允许查询自己的公司。"""
    if x_workspace_id != workspace_id:
        # 不允许查询其他公司——即使本地运行也做数据隔离
        raise HTTPException(status_code=404, detail="Workspace not found")
    c = workspace_module.get(workspace_id)
    if not c:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return c


@router.put("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    x_workspace_id: int = Depends(require_workspace),
):
    """更新公司字段。X-Workspace-ID 必须与目标公司匹配。"""
    if x_workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot update another workspace's record.")
    result = workspace_module.update(
        workspace_id,
        name=payload.name, logo_url=payload.logo_url, website=payload.website,
        contact_name=payload.contact_name, contact_email=payload.contact_email,
        address=payload.address, is_active=payload.is_active,
        custom_fields=payload.custom_fields,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return result


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    x_workspace_id: int = Depends(require_workspace),
    x_confirm_delete: str | None = Header(None, alias="X-Confirm-Delete"),
):
    """删除公司及级联删除其所有库、客户、对话记录。需要 X-Confirm-Delete header。"""
    if x_workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot delete another workspace.")
    if x_confirm_delete != "yes":
        raise HTTPException(
            status_code=400,
            detail="Destructive operation requires X-Confirm-Delete: yes header.",
        )
    if not workspace_module.delete(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"ok": True}


# ── 公司切换 ─────────────────────────────────────────────────────────────────

@router.post("/workspaces/{workspace_id}/switch")
def switch_workspace(
    workspace_id: int,
    request: Request,
):
    """显式切换当前 session 的活跃公司。

    切换后，后续所有请求的 X-Workspace-ID 必须匹配新公司。
    写审计日志记录切换操作。
    """
    # 校验目标公司存在且激活
    tc = workspace_module.get_workspace_record(workspace_id)
    if not tc or not tc.get("is_active"):
        raise HTTPException(status_code=404, detail="Workspace not found or inactive")

    token = request.headers.get("X-Hermes-Session-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")

    old_cid = None
    # 从 headers 获取当前活跃公司；切换请求必须显式声明来源公司
    x_cid = request.headers.get("X-Workspace-ID", "")
    if x_cid:
        try:
            old_cid = int(x_cid)
        except ValueError:
            raise HTTPException(status_code=401, detail="X-Workspace-ID must be an integer.")

    # 安全校验：切换请求的 X-Workspace-ID 必须等于目标公司
    # （前端 onCompanyChange 已先将 currentCompanyId 置为目标公司，再发起切换）
    # 防止未带 header 的请求任意绑定任意公司（首次绑定前的窗口期任选公司）
    if old_cid != workspace_id:
        raise HTTPException(
            status_code=403,
            detail="X-Workspace-ID header must match the target workspace for switch.",
        )

    set_active_workspace(token, workspace_id)

    # 写审计日志
    workspace_module._write_audit_log(
        workspace_id,
        "switch_workspace",
        f"Session switched active workspace (from={old_cid}, to={workspace_id})",
    )

    return {"active_workspace_id": workspace_id, "previous_workspace_id": old_cid}


# ── Agent 身份 ─────────────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/agent-identity")
def get_workspace_agent_identity(
    workspace_id: int,
    x_workspace_id: int = Depends(require_workspace),
):
    """获取公司的 Agent 身份文本（优先文件，其次 DB 缓存）。仅允许查自己的。"""
    if x_workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    identity = workspace_module.get_agent_identity(workspace_id)
    return {"workspace_id": workspace_id, "agent_identity_md": identity}


@router.put("/workspaces/{workspace_id}/agent-identity")
def update_workspace_agent_identity(
    workspace_id: int,
    payload: AgentIdentityUpdate,
    x_workspace_id: int = Depends(require_workspace),
):
    """更新公司的 Agent 身份。

    同时写 DB 与标准 identity 文件 —— 提示词解析是**文件优先**，
    只写 DB 会导致 UI 改了身份但提示词仍是旧内容。
    """
    if x_workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot update another workspace's identity.")
    result = workspace_module.update_workspace_record(
        workspace_id, agent_identity_md=payload.agent_identity_md,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workspace not found")

    slug = workspace_module.slug_from_id(workspace_id)
    if slug:
        from agentbase.prompts import write_agent_identity

        try:
            write_agent_identity(slug, payload.agent_identity_md)
        except OSError:
            # 文件写失败不回滚 DB：至少 DB 里是新内容，下次启动会用它
            pass
    return result
