"""连续同技能不能跳过技能正文注入（每次请求都是新 agent）。"""

from __future__ import annotations


def test_repeat_skill_still_injects_body(demo_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    import agentbase.workspace.crud as crud
    from agentbase import helpers
    from agentbase import workspace as ws
    from agentbase.api.chat import _extract_and_cache_skill
    from agentbase.database import init_db

    monkeypatch.setattr(crud, "AGENT_HOME", tmp_path)
    init_db()

    w = ws.create(name="Demo", slug="demo")
    full, hint = helpers.build_query(
        w["id"], "alpha 测试", last_skill_name="demo-alpha"
    )

    assert "## 技能触发：demo-alpha" in full
    assert "你是 demo-alpha 技能" in full
    assert _extract_and_cache_skill(w["id"], full, hint) == "demo-alpha"
