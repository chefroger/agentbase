"""文档分析铁律总纲落点（任务 1）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_mandate_in_accuracy_block_and_full_prompt():
    from agentbase import prompt

    mandate = "文档必须读完，不猜测，不截断，不以旧记忆编造。"
    assert mandate in prompt.DOCUMENT_ANALYSIS_MANDATE
    assert mandate in prompt.AGENTBASE_ACCURACY_BLOCK
    assert mandate in prompt.AGENTBASE_SYSTEM_PROMPT_FULL
    # 两处共用同一段，不重复拼接导致出现两次
    assert prompt.AGENTBASE_SYSTEM_PROMPT_FULL.count(mandate) == 1


def test_r0_to_r8_untouched():
    from agentbase import prompt

    for rule in ("R0:", "R1:", "R2:", "R4:", "R8:"):
        assert rule in prompt.AGENTBASE_SYSTEM_PROMPT_FULL


def test_framework_documents_mandate():
    text = (ROOT / "FRAMEWORK.md").read_text(encoding="utf-8")
    assert "文档必须读完，不猜测，不截断，不以旧记忆编造。" in text
    assert "document_task.py" in text
