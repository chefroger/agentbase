"""文档生成到“尚不存在”的输出路径时，仍要注入 FULL 指南。"""

from __future__ import annotations


def test_nonexistent_output_path_triggers_full_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    import agentbase.workspace.crud as crud
    from agentbase import helpers
    from agentbase import workspace as ws
    from agentbase.database import init_db

    monkeypatch.setattr(crud, "AGENT_HOME", tmp_path)
    init_db()
    w = ws.create(name="Demo", slug="demo")

    target = tmp_path / "new-report.docx"
    assert not target.exists()

    full, _ = helpers.build_query(w["id"], f"把分析结果导出到 {target}")

    assert "# Document Generation Guidelines" in full
    # 输出路径不存在，不能被当成“强制读取”的输入文件
    assert "用户指定文件（强制读取" not in full
