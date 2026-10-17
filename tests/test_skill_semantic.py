"""agentbase.skill_semantic 模块测试（用假 skill 注册表，不依赖真实项目）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentbase import skill_semantic  # noqa: E402
from agentbase.embeddings import TfidfBackend  # noqa: E402

FAKE_SKILLS = [
    {
        "name": "demo-alpha",
        "triggers": ["摘要", "结构化", "summarize", "summary"],
        "aliases": [],
        "input_fmt": "任意文本",
        "output_fmt": "结构化摘要",
    },
    {
        "name": "demo-beta",
        "triggers": ["文档分析", "document analysis", "读文档"],
        "aliases": [],
        "input_fmt": "文档路径",
        "output_fmt": "文档分析结果",
    },
    {
        "name": "demo-gamma",
        "triggers": ["会议纪要", "meeting notes", "纪要"],
        "aliases": [],
        "input_fmt": "会议记录",
        "output_fmt": "会议纪要",
    },
]


@pytest.fixture()
def router():
    r = skill_semantic.SemanticSkillRouter(skills=FAKE_SKILLS, backend=TfidfBackend())
    r.rebuild()
    return r


def test_build_documents():
    docs = skill_semantic.build_documents(FAKE_SKILLS)
    assert len(docs) == 3
    assert docs[0][0] == "demo-alpha"
    assert "摘要" in docs[0][1]


def test_search_exact_trigger(router):
    hits = router.search("帮我做个摘要")
    assert hits, "应命中 demo-alpha"
    assert hits[0]["skill_name"] == "demo-alpha"


def test_search_paraphrase(router):
    # 换个说法：关键词路由很可能 miss，语义应能兜住。
    # 注：min_score 是部署调参项（取决于真实 skill 集合 的 IDF 分布），
    # 这里用 min_score=0 断言排序质量本身。
    hits = router.search("把这段内容整理成结构化摘要", min_score=0.0)
    assert hits, "应有候选"
    assert hits[0]["skill_name"] == "demo-alpha"


def test_search_no_match(router):
    hits = router.search("今天天气怎么样")
    # 天气与所有 skill 都不相关，应被 min_score 过滤
    assert hits == []


def test_search_empty(router):
    assert router.search("") == []
    assert router.search("   ") == []


def test_hybrid_rank_merge():
    kw = [
        {"skill_name": "demo-alpha", "score": 3},
        {"skill_name": "demo-beta", "score": 1},
    ]
    sem = [
        {"skill_name": "demo-alpha", "score": 0.9},
        {"skill_name": "demo-gamma", "score": 0.8},
    ]
    ranked = skill_semantic.hybrid_rank(kw, sem, w_keyword=0.5, w_semantic=0.5)
    assert ranked[0]["skill_name"] == "demo-alpha"
    assert ranked[0]["source"] == "hybrid"
    # 只在语义出现的也应保留
    assert any(r["skill_name"] == "demo-gamma" for r in ranked)


def test_hybrid_rank_empty():
    assert skill_semantic.hybrid_rank([], []) == []


def test_match_skill_hybrid_confident_keyword(monkeypatch):
    # 关键词高置信时不走语义（router 单例不触发）
    monkeypatch.setenv("AGENTBASE_HYBRID_KEYWORD_CONFIDENT", "6")
    class FakeRouter:
        def _score_skills(self, q):
            return [{"skill_name": "demo-alpha", "score": 9}]

    import types

    fake_mod = types.ModuleType("agentbase.skill_router")
    fake_mod._score_skills = FakeRouter()._score_skills
    monkeypatch.setitem(sys.modules, "agentbase.skill_router", fake_mod)
    # 注意：skill_semantic 内部是 from agentbase import skill_router，
    # 这里通过 sys.modules 注入假模块
    import agentbase

    monkeypatch.setattr(agentbase, "skill_router", fake_mod, raising=False)
    best, alts = skill_semantic.match_skill_hybrid("摘要 结构化 summarize")
    assert best["skill_name"] == "demo-alpha"
    assert best["source"] == "keyword"


def test_match_skill_hybrid_never_raises(monkeypatch):
    # skill_router 抛错也要回退，不能抛到调用方
    import types

    fake_mod = types.ModuleType("agentbase.skill_router")

    def boom(q):
        raise RuntimeError("boom")

    fake_mod._score_skills = boom
    import agentbase

    monkeypatch.setattr(agentbase, "skill_router", fake_mod, raising=False)
    best, alts = skill_semantic.match_skill_hybrid("anything")
    assert best is None and alts == []


# ── 死锁回归（2026-10-13 集成时实测发现，外部包原生）─────────────────────────

def test_search_without_explicit_rebuild_does_not_deadlock():
    """首次 search() 走 `_ensure_built()` → `rebuild()` 的**嵌套加锁**路径。

    外部包的原始实现用不可重入的 `threading.Lock`：`_ensure_built` 持锁后
    调 `rebuild()`，后者再取同一把锁 → **永久死锁**（实测 `search()` 45s 不返回）。
    它的 30 个测试没暴露，是因为把 router 换成了 FakeRouter。

    这里用看门狗线程：回归时**断言失败**（15s 超时），而不是把 CI 挂死。
    """
    import threading

    from agentbase.skill_semantic import SemanticSkillRouter, reset_semantic_router

    reset_semantic_router()
    router = SemanticSkillRouter(
        skills=[{"name": "b2b-osint", "triggers": ["背调"], "aliases": ["查公司"]}]
    )
    out: dict = {}

    def _run():
        # min_score=0：本例只关心"能不能返回"，不掺阈值（阈值另有校准依据）
        out["hits"] = router.search("背调", min_score=0.0)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=15)
    assert not t.is_alive(), "search() 卡死 —— 锁又变成不可重入了（死锁回归）"
    assert out.get("hits"), "首次 search 应自动完成重建并返回候选"
    assert out["hits"][0]["skill_name"] == "b2b-osint"


def test_search_after_concurrent_first_calls_is_safe():
    """并发首调也不能死锁/崩（_ensure_built 的双检在锁内）。"""
    import threading

    from agentbase.skill_semantic import SemanticSkillRouter, reset_semantic_router

    reset_semantic_router()
    router = SemanticSkillRouter(skills=[{"name": "b2b-osint", "triggers": ["背调"]}])
    errors: list = []

    def _run():
        try:
            router.search("背调")
        except Exception as e:  # noqa: BLE001 —— 记下来，主线程断言
            errors.append(e)

    threads = [threading.Thread(target=_run, daemon=True) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)
    assert not any(t.is_alive() for t in threads), "并发首调卡死"
    assert not errors, f"并发首调抛错: {errors}"
