#!/usr/bin/env python3
"""验证三个扩展点真的能用（不是"代码还在"）：

  1. 第三方 Hermes plugin：从 $HERMES_HOME/plugins/ 加载并注册工具
  2. tools registry：注册的工具能被按 toolset 发现并调用
  3. MCP 客户端：连接一个 stdio MCP server，注册工具并实际调用

在临时目录里跑，不碰用户数据。用法：

    PYTHONPATH=vendor/hermes python scripts/verify_extensions.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor" / "hermes"))

PLUGIN_MANIFEST = """\
name: demo-plugin
version: 0.0.1
description: AgentBase extension verification plugin
provides_tools:
  - demo_ping
"""

PLUGIN_CODE = """\
def register(ctx):
    ctx.register_tool(
        name="demo_ping",
        toolset="demo",
        schema={
            "name": "demo_ping",
            "description": "Return pong:<value>",
            "parameters": {"type": "object", "properties": {"value": {"type": "string"}}},
        },
        handler=lambda value="": "pong:" + str(value),
        description="extension verification tool",
    )
"""

MCP_SERVER = """\
from mcp.server.mcpserver import MCPServer

server = MCPServer("demo-acceptance")

@server.tool()
def echo(text: str) -> str:
    \"\"\"Echo the given text with a prefix.\"\"\"
    return "echo:" + text

if __name__ == "__main__":
    server.run()
"""


def main() -> int:
    home = Path(tempfile.mkdtemp(prefix="agentbase-ext-"))
    os.environ["AGENT_HOME"] = str(home)
    os.environ["HERMES_HOME"] = str(home)
    os.environ.setdefault("HERMES_DISABLE_LAZY_INSTALLS", "1")

    # ── 1/2. plugin + tools registry ─────────────────────────────────────
    plugin_dir = home / "plugins" / "demo-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(PLUGIN_MANIFEST, encoding="utf-8")
    (plugin_dir / "__init__.py").write_text(PLUGIN_CODE, encoding="utf-8")
    (home / "config.yaml").write_text("plugins:\n  enabled:\n    - demo-plugin\n", encoding="utf-8")

    from hermes_cli.plugins import discover_plugins

    discover_plugins(force=True)

    from tools.registry import registry

    entry = registry.get_entry("demo_ping")
    assert entry is not None, "plugin 注册的 demo_ping 不在 tools registry 里"
    assert "demo_ping" in registry.get_tool_names_for_toolset("demo"), "toolset 发现失败"
    assert entry.handler(value="ok") == "pong:ok", "plugin 工具调用失败"
    print("✓ 1. 第三方 plugin 加载 + 工具注册")

    # ── 3. MCP ──────────────────────────────────────────────────────────
    server_py = home / "demo_mcp.py"
    server_py.write_text(MCP_SERVER, encoding="utf-8")
    (home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - demo-plugin\n"
        "mcp_servers:\n  demo:\n"
        f"    command: {sys.executable}\n"
        f"    args: [\"{server_py}\"]\n"
        "    enabled: true\n",
        encoding="utf-8",
    )

    from hermes_cli.config import load_config
    from tools.mcp_tool_discovery import register_mcp_servers

    names = register_mcp_servers(load_config().get("mcp_servers") or {})
    echo_name = next((n for n in names if n.endswith("__echo")), None)
    assert echo_name, f"MCP 工具未注册：{names}"

    tool = registry.get_entry(echo_name)
    assert tool is not None, "MCP 工具不在 registry 里"
    result = tool.handler({"text": "it-works"})
    assert "echo:it-works" in str(result), f"MCP 工具调用结果异常：{result}"

    print(f"✓ 2. tools registry 发现（{len(names)} 个 MCP 工具）")
    print("✓ 3. MCP 客户端连接 + 实际调用")
    print(f"\n全部通过（临时目录：{home}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
