"""
AgentBase — 对话记录 API 路由。

端点：
  GET    /conversations                   — 列出当前工作区的对话
  GET    /conversations/quality-stats     — 评分质量统计（低分技能/场景排行）
  POST   /conversations                   — 保存对话回合
  GET    /conversations/{conversation_id}  — 获取单条对话
  PUT    /conversations/{conversation_id}  — 更新对话回复
  DELETE /conversations/{conversation_id}  — 删除对话
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agentbase import chat_memory
from agentbase.api.deps import require_workspace
from agentbase.api.models import ConversationRate, ConversationSave, ConversationUpdate

router = APIRouter(tags=["conversations"])


@router.get("/conversations")
def list_conversations(
    context: str | None = None,
    limit: int = 50,
    x_workspace_id: int = Depends(require_workspace),
):
    """列出当前工作区的最近对话，可按上下文过滤。"""
    if context:
        return chat_memory.list_by_context(x_workspace_id, context, limit)
    return chat_memory.list_by_workspace(x_workspace_id, limit)


@router.get("/conversations/quality-stats")
def get_quality_stats(
    days: int = 30,
    x_workspace_id: int = Depends(require_workspace),
):
    """聚合当前工作区近 N 天的对话评分，返回按技能/场景聚合的均分与低分排行。

    用于质量追踪：快速看到哪些技能或入口场景的回复评分偏低，作为优化输入。
    注意：此路由必须声明在 /conversations/{conversation_id} 之前，
    否则 "quality-stats" 会被当作 conversation_id 解析。
    """
    return chat_memory.get_quality_stats(x_workspace_id, days=days)


@router.post("/conversations")
def save_conversation(
    payload: ConversationSave,
    x_workspace_id: int = Depends(require_workspace),
):
    """保存对话回合到 SQLite + Hindsight 长期记忆。"""
    return chat_memory.save_with_context(
        workspace_id=x_workspace_id,
        query=payload.query, response=payload.response,
        files_read=payload.files_read,
        context=payload.context or "",
        skill=payload.skill or "",
    )


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    x_workspace_id: int = Depends(require_workspace),
):
    """获取单条对话记录。"""
    conv = chat_memory.get(x_workspace_id, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.put("/conversations/{conversation_id}")
def update_conversation_response(
    conversation_id: int,
    payload: ConversationUpdate,
    x_workspace_id: int = Depends(require_workspace),
):
    """更新对话的回复字段。"""
    result = chat_memory.update_response(x_workspace_id, conversation_id, payload.response)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    x_workspace_id: int = Depends(require_workspace),
):
    """删除对话记录。"""
    if not chat_memory.delete(x_workspace_id, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.post("/conversations/{conversation_id}/rate")
def rate_conversation(
    conversation_id: int,
    payload: ConversationRate,
    x_workspace_id: int = Depends(require_workspace),
):
    """为对话记录评分（1-5）+ 可选反馈。"""
    result = chat_memory.add_rating(
        x_workspace_id, conversation_id, payload.rating, payload.feedback or "",
    )
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "conversation": result}
