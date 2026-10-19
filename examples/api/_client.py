"""示例共享客户端：从 /agentbase 页面取 session token，并封装请求。

用法：
    from _client import client, first_workspace, json_print

只依赖标准库 + requests（AgentBase 已安装）。
"""

from __future__ import annotations

import json
import os
import re
import sys

import requests

BASE = os.environ.get("AGENTBASE_URL", "http://127.0.0.1:9120").rstrip("/")
_TOKEN_RE = re.compile(r'let TOKEN = "([^"]+)"')


def session_token() -> str:
    resp = requests.get(f"{BASE}/agentbase", timeout=10)
    resp.raise_for_status()
    match = _TOKEN_RE.search(resp.text)
    if not match:
        raise RuntimeError(
            "未从 /agentbase 找到 token；请确认服务在本机运行，"
            "或设置 AGENTBASE_TOKEN 环境变量。"
        )
    return match.group(1)


TOKEN = os.environ.get("AGENTBASE_TOKEN") or session_token()


def headers(workspace_id: int | str | None = None) -> dict:
    result = {"X-Hermes-Session-Token": TOKEN}
    if workspace_id is not None:
        result["X-Workspace-ID"] = str(workspace_id)
    return result


def client() -> requests.Session:
    session = requests.Session()
    session.headers.update(headers())
    return session


def first_workspace() -> int:
    resp = requests.get(f"{BASE}/api/agentbase/workspaces", headers=headers(), timeout=10)
    resp.raise_for_status()
    workspaces = resp.json()
    if not workspaces:
        raise RuntimeError("没有可用的 workspace；请先在设置页创建工作区")
    return int(workspaces[0]["id"])


def json_print(data) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
