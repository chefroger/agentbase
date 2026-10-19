"""业务配置 API（business.yaml 的分层设置读写）。

- `GET  /business/config`：当前合并后的配置 + 方向预设。
- `PUT  /business/config`：原子更新指定字段（保留未知键），写后热加载。

这里不写 `skill_pack` —— 安装/启用技能包仍走 `/skill-packs/*`。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agentbase import business_config as biz
from agentbase import usage_directions

router = APIRouter(tags=["business-config"])


class OnboardingFieldUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(..., min_length=1, max_length=80)
    label_en: str | None = Field(None, max_length=80)
    example: str = Field("", max_length=200)
    example_en: str | None = Field(None, max_length=200)


class BrandingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, max_length=80)
    welcome: str | None = Field(None, max_length=500)
    logo: str | None = Field(None, max_length=500)


class WorkDirUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., pattern=r"^[A-Za-z0-9_-]{1,40}$")
    description: str = Field("", max_length=120)


class PromptOverridesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: str | None = Field(None, max_length=20000)


class WorkspaceFieldUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(..., min_length=1, max_length=80)
    type: str = Field("text", pattern=r"^text$")


class WorkspacesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str | None = Field(None, min_length=1, max_length=40)
    term_en: str | None = Field(None, min_length=1, max_length=40)
    mode: str | None = Field(None, pattern=r"^(single|multi)$")
    create_default: bool | None = None
    fields: list[WorkspaceFieldUpdate] | None = Field(None, max_length=20)


class UiModuleUpdate(BaseModel):
    """业务前端模块（本次只预留 schema，加载器后续实现）。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(..., min_length=1, max_length=60)
    label_en: str | None = Field(None, max_length=60)
    entry: str = Field("", max_length=500)


class UiUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modules: list[UiModuleUpdate] | None = Field(None, max_length=20)


class BusinessConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = Field(None, min_length=1, max_length=80)
    tagline: str | None = Field(None, max_length=200)
    usage_direction: str | None = None
    onboarding_fields: list[OnboardingFieldUpdate] | None = Field(None, min_length=1, max_length=20)
    branding: BrandingUpdate | None = None
    work_dirs: list[WorkDirUpdate] | None = Field(None, min_length=1, max_length=10)
    prompt_overrides: PromptOverridesUpdate | None = None
    workspaces: WorkspacesUpdate | None = None
    ui: UiUpdate | None = None


@router.get("/business/config")
def get_business_config() -> dict:
    """返回合并后的业务配置 + 全部方向预设。"""
    return {
        "ok": True,
        "path": str(biz.config_path()),
        "config": biz.load(),
        "usage_direction": biz.usage_direction(),
        "directions": usage_directions.list_presets(),
    }


@router.put("/business/config")
def update_business_config(payload: BusinessConfigUpdate) -> dict:
    """原子更新 business.yaml 中出现的字段；未出现的保持原值。"""
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)

    direction = updates.get("usage_direction")
    if direction is not None and not usage_directions.is_valid_direction(direction):
        raise HTTPException(
            status_code=400,
            detail=f"未知的使用方向 {direction!r}；合法值：{', '.join(usage_directions.direction_ids())}",
        )

    workspaces = updates.get("workspaces") or {}
    mode = workspaces.get("mode")
    if mode is not None and mode not in ("single", "multi"):
        raise HTTPException(status_code=400, detail="workspaces.mode 只能是 single 或 multi")

    if not updates:
        return {"ok": True, "config": biz.load(), "changed": []}

    try:
        config = biz.write_updates(updates)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"写入 business.yaml 失败：{exc}") from exc

    return {"ok": True, "config": config, "changed": sorted(updates)}
