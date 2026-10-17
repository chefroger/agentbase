"""审计 #8：`_patch_yaml_list` 必须是**逐项精确**匹配。

子串匹配会让已有 `chat-memory-pro` 被误判成"已包含 chat-memory"，从而静默不追加。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase.bootstrap import _patch_yaml_list  # noqa: E402


def test_inline_list_requires_exact_item():
    text = "plugins:\n  enabled: [chat-memory-pro]\n"

    out = _patch_yaml_list(text, ("plugins", "enabled"), "chat-memory")

    assert "chat-memory-pro, chat-memory" in out.replace('"', "").replace("'", "")


def test_exact_item_is_idempotent():
    text = "plugins:\n  enabled: [chat-memory]\n"

    assert _patch_yaml_list(text, ("plugins", "enabled"), "chat-memory") == text


def test_multiline_list_requires_exact_item():
    text = "plugins:\n  enabled:\n    - chat-memory-pro\n"

    out = _patch_yaml_list(text, ("plugins", "enabled"), "chat-memory")

    assert "- chat-memory\n" in out
