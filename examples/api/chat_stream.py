"""SSE 流式聊天示例：逐事件打印 thinking/tool/response/done。"""

from __future__ import annotations

import json
import sys

import requests

from _client import BASE, first_workspace, headers


def stream_chat(query: str, workspace_id: int) -> None:
    with requests.post(
        f"{BASE}/api/agentbase/chat/stream",
        headers=headers(workspace_id),
        json={"query": query, "language": "zh"},
        stream=True,
        timeout=1800,
    ) as resp:
        resp.raise_for_status()
        event = None
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or raw.startswith(":"):
                continue
            if raw.startswith("event: "):
                event = raw[len("event: "):]
            elif raw.startswith("data: ") and event:
                data = json.loads(raw[len("data: "):])
                if event == "response":
                    print("\n--- response ---")
                    print(data.get("text", ""))
                else:
                    print(f"[{event}] {json.dumps(data, ensure_ascii=False)[:300]}")
                if event == "done":
                    return


def main() -> None:
    query = " ".join(sys.argv[1:]) or "用一句话介绍你自己"
    stream_chat(query, first_workspace())


if __name__ == "__main__":
    main()
