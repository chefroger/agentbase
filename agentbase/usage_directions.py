"""使用方向预设（business.yaml.usage_direction）。

这是「方向 → 推荐」的唯一事实来源：前端只渲染后端返回的预设，
不在前端写死任何方向或业务字段。选择方向**不会自动覆盖**用户配置，
由用户点击「应用推荐」后再写入。
"""

from __future__ import annotations

from typing import Any

DIRECTION_PRESETS: list[dict[str, Any]] = [
    {
        "id": "general",
        "label": "通用助手",
        "label_en": "General assistant",
        "description": "日常问答、写作与资料整理，不绑定具体行业。",
        "description_en": "Everyday Q&A, writing, and document organization.",
        "default_business_name": "我的助手",
        "default_business_name_en": "My Assistant",
        "onboarding_fields": [
            {"key": "role", "label": "助手角色", "label_en": "Assistant role",
             "example": "AI 业务助手", "example_en": "AI assistant"},
            {"key": "products", "label": "产品/服务", "label_en": "Products/services",
             "example": "请填写主要产品或服务", "example_en": "Your main product or service"},
            {"key": "audience", "label": "目标客户", "label_en": "Target audience",
             "example": "请填写目标客户群", "example_en": "Who you serve"},
        ],
        "recommended_skill_pack": "",
        "recommended_skill_pack_reason": "",
        "recommended_skill_pack_reason_en": "",
        "workspaces": {"term": "工作区", "term_en": "Workspace",
                       "mode": "single", "create_default": True},
    },
    {
        "id": "document-analysis",
        "label": "文档分析",
        "label_en": "Document analysis",
        "description": "以文件上传、解析、逐页核对与汇总为主。",
        "description_en": "Upload, parse, verify and summarize documents.",
        "default_business_name": "文档助手",
        "default_business_name_en": "Document Assistant",
        "onboarding_fields": [
            {"key": "role", "label": "助手角色", "label_en": "Assistant role",
             "example": "文档分析助手", "example_en": "Document analyst"},
            {"key": "document_types", "label": "主要文档类型", "label_en": "Document types",
             "example": "合同、报表、扫描件", "example_en": "Contracts, reports, scans"},
            {"key": "output", "label": "期望输出", "label_en": "Expected output",
             "example": "摘要、核对清单、差异报告", "example_en": "Summary, checklist, diff report"},
        ],
        "recommended_skill_pack": "demo-pack",
        "recommended_skill_pack_reason": "仓库自带示例包，可先验证技能路由；正式部署时替换为文档类技能包。",
        "recommended_skill_pack_reason_en": "Bundled demo pack for validating skill routing; replace it with a document-oriented pack for production.",
        "workspaces": {"term": "项目", "term_en": "Project",
                       "mode": "multi", "create_default": False},
    },
    {
        "id": "customer-research",
        "label": "客户研究",
        "label_en": "Customer research",
        "description": "围绕客户/线索的资料整理、画像与跟进记录。",
        "description_en": "Organize customer/lead information, profiles and follow-ups.",
        "default_business_name": "研究助手",
        "default_business_name_en": "Research Assistant",
        "onboarding_fields": [
            {"key": "role", "label": "助手角色", "label_en": "Assistant role",
             "example": "客户研究助手", "example_en": "Customer research assistant"},
            {"key": "target", "label": "研究对象", "label_en": "Research target",
             "example": "潜在客户、渠道伙伴", "example_en": "Prospects, channel partners"},
            {"key": "sources", "label": "常用信息来源", "label_en": "Information sources",
             "example": "官网、公开数据库、会议记录", "example_en": "Websites, public databases, meeting notes"},
        ],
        "recommended_skill_pack": "",
        "recommended_skill_pack_reason": "客户研究类技能包尚未内置，可先通过 MCP/tools 扩展或自建 skill pack。",
        "recommended_skill_pack_reason_en": "No bundled customer-research pack yet; extend via MCP/tools or build your own pack.",
        "workspaces": {"term": "客户", "term_en": "Customer",
                       "mode": "multi", "create_default": False},
    },
    {
        "id": "custom",
        "label": "自定义",
        "label_en": "Custom",
        "description": "不套用预设，自行配置业务名称、字段与工作区语义。",
        "description_en": "Configure the business name, fields and workspace semantics yourself.",
        "default_business_name": "我的业务",
        "default_business_name_en": "My Business",
        "onboarding_fields": [],
        "recommended_skill_pack": "",
        "recommended_skill_pack_reason": "",
        "recommended_skill_pack_reason_en": "",
        "workspaces": {"term": "工作区", "term_en": "Workspace",
                       "mode": "single", "create_default": True},
    },
]

_BY_ID = {preset["id"]: preset for preset in DIRECTION_PRESETS}


def list_presets() -> list[dict[str, Any]]:
    """返回全部预设的深拷贝，调用方可安全修改。"""
    import copy

    return copy.deepcopy(DIRECTION_PRESETS)


def get_preset(direction_id: str) -> dict[str, Any] | None:
    preset = _BY_ID.get(str(direction_id or "").strip())
    if preset is None:
        return None
    import copy

    return copy.deepcopy(preset)


def is_valid_direction(direction_id: str) -> bool:
    return str(direction_id or "").strip() in _BY_ID


def direction_ids() -> list[str]:
    return [preset["id"] for preset in DIRECTION_PRESETS]
