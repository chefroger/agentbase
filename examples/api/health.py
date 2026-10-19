"""基础连通性示例：status / branding / workspaces / settings。"""

from __future__ import annotations

import requests

from _client import BASE, headers, json_print


def main() -> None:
    status = requests.get(f"{BASE}/api/status", timeout=10).json()
    print("== /api/status ==")
    json_print({k: status.get(k) for k in ("status", "version", "hermes_usable")})

    branding = requests.get(f"{BASE}/api/agentbase/branding", timeout=10).json()
    print("== /api/agentbase/branding ==")
    json_print({
        "business_name": branding.get("business_name"),
        "usage_direction": branding.get("usage_direction"),
        "workspaces": branding.get("workspaces"),
    })

    workspaces = requests.get(
        f"{BASE}/api/agentbase/workspaces", headers=headers(), timeout=10
    ).json()
    print("== workspaces ==")
    json_print(workspaces)

    settings = requests.get(
        f"{BASE}/api/agentbase/settings", headers=headers(), timeout=10
    ).json()
    print("== settings (摘要) ==")
    json_print({
        "active": settings.get("active"),
        "configured_provider_count": settings.get("configured_provider_count"),
        "moa": settings.get("moa"),
        "agent_behavior": settings.get("agent_behavior"),
    })


if __name__ == "__main__":
    main()
