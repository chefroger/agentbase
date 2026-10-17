"""许可证 API 路由。

- ``GET /license/status``：**免 session token**（登录前就要显示品牌/剩余天数/申请码）。
  许可证是机器级的（一台电脑一份），不按 workspace 隔离，因此不接受 X-Workspace-ID。
- ``POST /license/activate``：**需要 session token**——这是写操作（落盘 license.json），
  不能允许任意本地进程/网页跨站触发。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agentbase.api.deps import require_session
from agentbase.license import activate as _activate
from agentbase.license import status as _status

router = APIRouter(tags=["license"])


class ActivateRequest(BaseModel):
    code: str


@router.get("/license/status")
def license_status():
    """返回本机许可证状态（登录前可用）。"""
    return _status()


@router.post("/license/activate", dependencies=[Depends(require_session)])
def license_activate(payload: ActivateRequest):
    """激活本机许可证。"""
    ok, msg = _activate(payload.code)
    if not ok:
        return {"ok": False, "error": msg}
    return {"ok": True, "message": msg}
