"""
AgentBase — API 请求/响应模型（Pydantic）。

只包含框架级模型。业务模型（客户 / 订单 / 文档库）由 skill 包通过自己的 API 提供。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# ── Workspace（当前模块名仍为 workspace，P3 改名批次统一处理）────────────────


class WorkspaceCreate(BaseModel):
    name: str = Field(..., description="workspace 名称")
    slug: str | None = Field(None, description="URL 标识（省略时自动生成）")
    logo_url: str = Field("", description="Logo URL")
    website: str = Field("", description="网站")
    contact_name: str = Field("", description="联系人姓名")
    contact_email: str = Field("", description="联系人邮箱")
    address: str = Field("", description="地址")
    work_dir_name: str = Field("", description="工作目录名称（目录存在时可用此改名）")


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, description="workspace 名称")
    logo_url: str | None = Field(None, description="Logo URL")
    website: str | None = Field(None, description="网站")
    contact_name: str | None = Field(None, description="联系人姓名")
    contact_email: str | None = Field(None, description="联系人邮箱")
    address: str | None = Field(None, description="地址")
    is_active: bool | None = Field(None, description="是否激活")


class AgentIdentityUpdate(BaseModel):
    agent_identity_md: str = Field("", description="Agent 身份配置 (Markdown)")


class OnboardingFirstWorkspace(BaseModel):
    workspace_name: str = Field(..., description="workspace 名称")
    contact_name: str = Field("", description="联系人姓名")
    contact_email: str = Field("", description="联系人邮箱")
    identity_data: dict | None = Field(None, description="Agent 身份配置")
    work_dir_name: str = Field("", description="工作目录名称")


# ── Conversation ───────────────────────────────────────────────────────────────

class ConversationRate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    feedback: str | None = Field(None, description="可选反馈文字")


class ConversationSave(BaseModel):
    query: str = Field(..., description="用户问题")
    response: str = Field("", description="Agent 回复")
    files_read: list[dict] = Field(default_factory=list, description="读取的文件列表")
    context: str = Field("", description="聊天上下文")
    skill: str = Field("", description="本次匹配到的技能名（供质量统计，可选）")


class ConversationUpdate(BaseModel):
    response: str = Field(..., description="更新后的回复内容")


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100000, description="用户问题（1-100000 字符）")
    context: str = Field("", description="聊天上下文")
    language: str = Field("zh", description="界面语言 zh/en")

    @field_validator("language", mode="before")
    @classmethod
    def _default_language(cls, v):
        return v or "zh"
