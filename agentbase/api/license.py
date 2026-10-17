"""许可证 API 路由（不需要 session token，但需要 workspace_id 做多租户隔离）。"""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from agentbase.license import activate as _activate
from agentbase.license import status as _status

router = APIRouter(tags=["license"])


class ActivateRequest(BaseModel):
    code: str
    workspace_id: int | None = None


def _parse_workspace_id(x_workspace_id: str | None = Header(None, alias="X-Workspace-ID")) -> int | None:
    """解析 X-Workspace-ID header 为整数，缺失或无效时返回 None。"""
    if not x_workspace_id or not x_workspace_id.strip():
        return None
    try:
        return int(x_workspace_id.strip())
    except ValueError:
        return None


@router.get("/license/status")
def license_status(cid: int | None = Depends(_parse_workspace_id)):
    """返回指定公司的许可证状态。未传 workspace_id 时返回首个激活公司的状态。"""
    return _status(workspace_id=cid)


@router.post("/license/activate")
def license_activate(payload: ActivateRequest):
    """激活指定公司的许可证。"""
    ok, msg = _activate(payload.code, workspace_id=payload.workspace_id)
    if not ok:
        return {"ok": False, "error": msg}
    return {"ok": True, "message": msg}
