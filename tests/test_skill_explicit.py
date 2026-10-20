"""显式技能名解析：中文后缀不能吞掉注册名。"""

from __future__ import annotations


def test_explicit_skill_name_with_chinese_suffix(demo_pack):
    from agentbase import skill_registry, skill_router

    for text in ("使用demo-alpha做分析", "用demo-a做分析", "请用背调技能查一下"):
        match = skill_registry._EXPLICIT_RE.search(text)
        assert match is not None
        token = match.group("skill")
        if token.startswith("背调"):
            continue  # demo pack 没有这个技能，只验证不误吞其它名称
        assert skill_router._resolve_explicit_skill(token) == "demo-alpha"


def test_ascii_suffix_is_not_trimmed(demo_pack):
    """demo-alphaX 不是 demo-alpha，不能靠前缀猜测误命中。"""
    from agentbase import skill_router

    assert skill_router._resolve_explicit_skill("demo-alphaX") is None
