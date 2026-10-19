"""
品牌配置 API。

前端启动时先取 `/api/branding` 再渲染标题/欢迎语 —— 框架自带中性默认值，
业务通过 `~/.agentbase/business.yaml` 的 `branding` 段覆盖。
不需要 session token（登录前就要显示品牌）。
"""

from __future__ import annotations

from fastapi import APIRouter

from agentbase import business_config

router = APIRouter(tags=["branding"])


@router.get("/branding")
def get_branding() -> dict:
    """返回当前业务的前端品牌信息。"""
    config = business_config.load()
    branding = dict(config.get("branding") or {})
    return {
        "title": branding.get("title") or "AgentBase",
        "welcome": branding.get("welcome") or "你好，我是你的业务助手。",
        "logo": branding.get("logo") or "",
        "business_name": config.get("business_name") or "AgentBase",
        "tagline": config.get("tagline") or "",
        "usage_direction": business_config.usage_direction(),
        # workspace 的用户可见称呼（公司/项目/客户/门店…），由 business.yaml 定义
        "workspaces": {
            "term": business_config.workspace_term("zh"),
            "term_en": business_config.workspace_term("en"),
            "mode": business_config.workspaces_config().get("mode", "single"),
        },
        # 前端上传弹窗要用的目录清单
        "work_dirs": business_config.work_dir_names(),
        # 通用 onboarding 表单字段（框架不含业务字段）
        "onboarding_fields": business_config.onboarding_fields(),
    }
