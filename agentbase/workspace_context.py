"""当前会话的 workspace 上下文（服务端可信来源）。

为什么需要它：插件工具（如 chat_memory_list）需要知道"当前对话属于哪个 workspace"。
若把这个值作为 LLM 可写的工具参数，模型就可能传错（读到别的工作区数据）。
这里由 agentbase 在**发起 agent 调用时**绑定，插件只读不写。

ContextVar 而非线程局部：Hermes 的工具执行线程会通过
``tools/thread_context.propagate_context_to_thread`` 复制当前 ContextVar 上下文，
所以绑定值能安全地跨到工具执行 worker。
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_CURRENT_WORKSPACE: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "agentbase_current_workspace_id", default=None,
)


def current_workspace_id() -> int | None:
    """返回当前 agent 调用绑定的 workspace ID；未绑定时为 None。"""
    return _CURRENT_WORKSPACE.get()


@contextmanager
def bind_workspace(workspace_id: int | None) -> Iterator[None]:
    """在 with 块内把 workspace_id 绑定为当前上下文。"""
    token = _CURRENT_WORKSPACE.set(workspace_id)
    try:
        yield
    finally:
        _CURRENT_WORKSPACE.reset(token)
