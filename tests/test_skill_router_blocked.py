"""Skill 路由的**框架级机制**测试。

只依赖 `tests/fixtures/demo-pack`（中性 fixture），不依赖任何业务 skill ——
业务路由断言的覆盖在 trade-business-pack 仓库里，见 docs/EXTRACTED-CAPABILITIES.md。

覆盖：blocked 过滤、注册表完整性、QA 对解析/评分/注入。
"""

from __future__ import annotations


class TestBlockedSkills:
    """`blocked_skills` 里的 skill 不得被任何匹配路径触发。"""

    def test_blocked_skill_not_scored(self, demo_pack):
        from agentbase.skill_router import _score_skills

        results = _score_skills("禁用演示")
        names = [r["skill_name"] for r in results]
        assert "demo-blocked" not in names, f"blocked skill 出现在评分结果中: {names}"

    def test_blocked_skill_not_matched_by_match_skill(self, demo_pack):
        from agentbase.skill_router import match_skill

        result = match_skill("blocked")
        assert result is None or result["name"] != "demo-blocked"

    def test_blocked_skill_not_matched_by_match_skills(self, demo_pack):
        from agentbase.skill_router import match_skills

        results = match_skills("禁用演示 blocked")
        names = [r["skill_name"] for r in results]
        assert "demo-blocked" not in names

    def test_blocked_skill_is_registered_as_blocked(self, demo_pack):
        from agentbase.skill_registry import _BLOCKED_SKILLS

        assert "demo-blocked" in _BLOCKED_SKILLS
        # 没被 block 的同类 skill 不应被误伤（旧实现的子串匹配曾误伤 chat-memory-pro）
        assert "demo-alpha" not in _BLOCKED_SKILLS
        assert "demo-beta" not in _BLOCKED_SKILLS


class TestRegistryLoading:
    """注册表来自 pack，加载结果必须与 pack 声明一致。"""

    def test_all_skills_loaded_from_pack(self, demo_pack):
        from agentbase.skill_registry import _SKILLS

        assert len(_SKILLS) == 3

    def test_skill_names_unique(self, demo_pack):
        from agentbase.skill_registry import _SKILLS

        names = [s["name"] for s in _SKILLS]
        assert len(names) == len(set(names))

    def test_empty_registry_without_pack(self, monkeypatch):
        """没有配置 skill pack 时注册表为空 —— 框架照常可用（降级，不是错误）。"""
        from agentbase import skill_registry

        monkeypatch.delenv("AGENTBASE_SKILL_PACK", raising=False)
        before = list(skill_registry._SKILLS)
        try:
            monkeypatch.setattr(skill_registry, "active_skill_pack", lambda: None)
            count = skill_registry.load_active_pack()
            assert count == 0
            assert skill_registry.skill_names() == []
        finally:
            skill_registry._SKILLS[:] = before
            skill_registry._BLOCKED_SKILLS = frozenset()

    def test_missing_pack_dir_degrades_to_empty(self, monkeypatch, tmp_path):
        """pack 路径写错不应抛异常 —— 只是没有业务技能。"""
        from agentbase import skill_registry

        monkeypatch.setenv("AGENTBASE_SKILL_PACK", str(tmp_path / "does-not-exist"))
        assert skill_registry.skill_names() == []
        assert skill_registry.load_pack(tmp_path / "does-not-exist") == ([], frozenset())

    def test_pack_manifest_exposes_doc_task_skills(self, demo_pack):
        from agentbase.skill_registry import pack_manifest

        assert pack_manifest().get("doc_task_skills") == ["demo-beta"]


class TestQAPairs:
    """QA 对的解析、加载、评分与注入（机制，与业务内容无关）。"""

    def test_parse_qa_pairs(self):
        from agentbase.skill_router import _parse_qa_pairs

        content = """## Q1: alpha 的核心目标是什么？
**答案**: 把输入整理成结构化摘要。
**标签**: 摘要原则, 结构化
**场景**: 任何 alpha 任务
**关键词**: alpha, 摘要, 结构化

## Q2: alpha 如何处理长文本？
**答案**: 先分段，再逐段提取要点。
**标签**: 长文本
**场景**: 输入很长时
**关键词**: 长文本, 分段, 要点
"""
        pairs = _parse_qa_pairs(content)
        assert len(pairs) == 2
        assert pairs[0]["q"] == "alpha 的核心目标是什么？"
        assert pairs[0]["tags"] == ["摘要原则", "结构化"]
        assert pairs[0]["keywords"] == ["alpha", "摘要", "结构化"]
        assert pairs[1]["q"] == "alpha 如何处理长文本？"

    def test_parse_qa_pairs_empty(self):
        from agentbase.skill_router import _parse_qa_pairs

        assert _parse_qa_pairs("") == []
        assert _parse_qa_pairs("只是一些文字没有QA格式") == []

    def test_load_qa_pairs_from_pack(self, demo_pack):
        """QA 对必须能从 skill pack 的 references/ 里加载。"""
        from agentbase.skill_router import _load_qa_pairs

        pairs = _load_qa_pairs("demo-alpha")
        assert len(pairs) == 2
        for p in pairs:
            assert p["q"] and p["a"]
            assert isinstance(p["tags"], list)
            assert isinstance(p["keywords"], list)

    def test_load_qa_pairs_nonexistent(self, demo_pack):
        from agentbase.skill_router import _load_qa_pairs

        assert _load_qa_pairs("nonexistent-skill") == []
        # demo-beta 没有 qa_pairs.md
        assert _load_qa_pairs("demo-beta") == []

    def test_score_qa_relevance_chinese(self, demo_pack):
        from agentbase.skill_router import _load_qa_pairs, _score_qa_relevance

        pairs = _load_qa_pairs("demo-alpha")
        relevant = _score_qa_relevance("alpha 怎么处理长文本", pairs)
        assert len(relevant) > 0
        assert len(relevant) <= 5

    def test_score_qa_relevance_no_match(self, demo_pack):
        from agentbase.skill_router import _load_qa_pairs, _score_qa_relevance

        pairs = _load_qa_pairs("demo-alpha")
        assert _score_qa_relevance("今天天气真好", pairs) == []

    def test_augment_query_includes_qa(self, demo_pack):
        from agentbase.skill_router import augment_query

        result = augment_query("alpha 怎么处理长文本")
        assert "相关知识（精准匹配）" in result

    def test_augment_query_no_qa_for_skill_without_pairs(self, demo_pack):
        from agentbase.skill_router import augment_query

        result = augment_query("beta 文档分析")
        assert "相关知识（精准匹配）" not in result
