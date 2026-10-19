"""用户数据目录解析 —— 唯一权威实现。

AgentBase 与随附的 Hermes 共用同一个数据根：
  1. ``HERMES_HOME`` 显式设置（安装器 / 测试）→ 用它
  2. 否则 ``AGENT_HOME`` 显式设置 → 用它
  3. 否则平台默认：Windows ``%LOCALAPPDATA%\\agentbase``，其他 ``~/.agentbase``

**绝不回退到用户的 ``~/.hermes``** —— 用户机器上可能装着独立 Hermes / OpenClaw，
随附运行时必须与它物理隔离（任务书 v2 §10.7 / §10.9）。
"""

from __future__ import annotations

import os
from pathlib import Path


def agent_home() -> Path:
    """AgentBase 数据根（``AGENT_HOME`` → 平台默认 ``~/.agentbase``）。"""
    val = os.environ.get("AGENT_HOME", "").strip()
    if val:
        return Path(val)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local) / "agentbase"
    return Path.home() / ".agentbase"


def hermes_home() -> Path:
    """随附 Hermes 的数据根；未显式设置时与 :func:`agent_home` 相同。"""
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val)
    return agent_home()
