"""Skill 包示例：列出 / 安装 / 启用 / 卸载。

用法：
    python packs.py list
    python packs.py install /absolute/path/to/pack
    python packs.py activate <name>
    python packs.py remove <name>
"""

from __future__ import annotations

import sys

import requests

from _client import BASE, headers, json_print


def main() -> None:
    base = f"{BASE}/api/agentbase/skill-packs"
    action = sys.argv[1] if len(sys.argv) > 1 else "list"

    if action == "list":
        json_print(requests.get(base, headers=headers(), timeout=10).json())
    elif action == "install":
        path = sys.argv[2]
        resp = requests.post(
            f"{base}/install", headers=headers(), json={"path": path}, timeout=60
        )
        json_print(resp.json())
    elif action == "activate":
        name = sys.argv[2]
        resp = requests.post(
            f"{base}/activate", headers=headers(), json={"name": name}, timeout=30
        )
        json_print(resp.json())
    elif action == "remove":
        name = sys.argv[2]
        resp = requests.delete(f"{base}/{name}", headers=headers(), timeout=30)
        json_print(resp.json())
    else:
        raise SystemExit("未知操作；可用：list/install/activate/remove")


if __name__ == "__main__":
    main()
