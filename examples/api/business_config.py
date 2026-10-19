"""业务配置示例：读取方向预设，切换到「文档分析」并设置 workspace 语义。

注意：会改写 ~/.agentbase/business.yaml。运行前可先备份。
"""

from __future__ import annotations

import requests

from _client import BASE, headers, json_print


def main() -> None:
    url = f"{BASE}/api/agentbase/business/config"

    current = requests.get(url, headers=headers(), timeout=10).json()
    print("== 当前方向 ==", current.get("usage_direction"))
    print("== 可用方向 ==")
    for preset in current.get("directions", []):
        print(f"- {preset['id']}: {preset['label']}")

    preset = next(
        (p for p in current["directions"] if p["id"] == "document-analysis"), None
    )
    if preset is None:
        raise SystemExit("未找到 document-analysis 预设")

    update = {
        "usage_direction": "document-analysis",
        "business_name": preset["default_business_name"],
        # 去掉仅用于展示的英文键，保持后端 schema 干净
        "onboarding_fields": [
            {k: v for k, v in field.items() if k in ("key", "label", "example")}
            for field in preset["onboarding_fields"]
        ],
        "workspaces": preset["workspaces"],
    }

    resp = requests.put(url, headers=headers(), json=update, timeout=10)
    resp.raise_for_status()
    print("== 已更新 ==")
    json_print({
        "changed": resp.json().get("changed"),
        "usage_direction": resp.json()["config"].get("usage_direction"),
        "workspaces": resp.json()["config"].get("workspaces"),
    })


if __name__ == "__main__":
    main()
