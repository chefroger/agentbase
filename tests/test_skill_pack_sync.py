"""skill pack 后台检查：只 fetch 比对，绝不 pull；状态可见。

任务书红线：改完后任何未经用户动作的 git pull 不得再发生。这些用例同时
钉住「工作区零变更」与「状态记录/doctor 可见」两件事。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "git", "-c", "user.email=test@example.com", "-c", "user.name=test",
            *args,
        ],
        cwd=cwd, check=True, capture_output=True, text=True,
    )


def _git_out(cwd: Path, *args: str) -> str:
    return _git(cwd, *args).stdout.strip()


def _snapshot(root: Path) -> dict[str, bytes]:
    """工作区文件快照（排除 .git，fetch 只允许改它）。"""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


@pytest.fixture
def pack_repo(tmp_path, monkeypatch):
    """本地 bare 远端 + seed 仓库 + pack 克隆，全离线。"""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AGENT_HOME", str(home))

    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    (seed / "skills" / "demo").mkdir(parents=True)
    (seed / "skills" / "demo" / "SKILL.md").write_text("v1\n", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "init")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", "main")

    pack = tmp_path / "pack"
    _git(tmp_path, "clone", "-q", str(remote), str(pack))
    monkeypatch.setenv("AGENTBASE_SKILL_PACK", str(pack))

    def _advance() -> None:
        (seed / "skills" / "demo" / "SKILL.md").write_text("v2\n", encoding="utf-8")
        _git(seed, "add", "-A")
        _git(seed, "commit", "-m", "v2")
        _git(seed, "push", "origin", "main")

    return {"pack": pack, "home": home, "advance": _advance}


def test_no_pack_status_has_all_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.delenv("AGENTBASE_SKILL_PACK", raising=False)

    from agentbase.post_install.skills import check_skill_pack_update

    status = check_skill_pack_update()

    assert status["status"] == "no_pack"
    assert set(status) == {
        "pack", "path", "local_commit", "remote_commit", "upstream",
        "behind", "status", "error", "checked_at",
    }


def test_check_reports_update_without_touching_worktree(pack_repo):
    from agentbase.post_install.skills import check_skill_pack_update

    pack = pack_repo["pack"]
    before_head = _git_out(pack, "rev-parse", "HEAD")
    before_files = _snapshot(pack)

    pack_repo["advance"]()
    status = check_skill_pack_update()

    assert status["status"] == "update_available"
    assert status["behind"] == 1
    assert status["local_commit"] == before_head
    assert status["remote_commit"] != status["local_commit"]
    assert status["pack"] == "pack"

    # 红线：检查只读，工作区与 HEAD 都不能变（绝无 pull）
    assert _snapshot(pack) == before_files
    assert _git_out(pack, "rev-parse", "HEAD") == before_head
    assert _git_out(pack, "status", "--porcelain") == ""


def test_background_check_once_records_status(pack_repo):
    from agentbase.bootstrap import check_skill_pack_sync_once
    from agentbase.post_install.skills import (
        load_skill_pack_status,
        skill_pack_status_path,
    )

    pack_repo["advance"]()
    before_files = _snapshot(pack_repo["pack"])

    status = check_skill_pack_sync_once()

    assert status["status"] == "update_available"
    stored = load_skill_pack_status()
    assert stored is not None
    assert set(stored) == {
        "pack", "path", "local_commit", "remote_commit", "upstream",
        "behind", "status", "error", "checked_at",
    }
    assert stored["status"] == "update_available"
    assert stored["behind"] == 1
    assert stored["checked_at"]
    assert skill_pack_status_path().is_file()
    assert _snapshot(pack_repo["pack"]) == before_files


def test_update_skills_refreshes_status(pack_repo, monkeypatch):
    """所有手动更新路径（CLI / 系统更新 / API）共用 update_skills：

    更新成功后必须立刻刷新状态，doctor 不能继续显示「有新提交」。
    """
    from agentbase import skill_registry
    from agentbase.post_install import skills as skills_mod

    hermes = pack_repo["home"] / "hermes"
    hermes.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes))
    pack_repo["advance"]()

    try:
        skills_mod.update_skills()

        stored = skills_mod.load_skill_pack_status()
        assert stored is not None
        assert stored["status"] == "up_to_date"
        assert stored["behind"] == 0
        assert stored["local_commit"] == stored["remote_commit"]
        assert _git_out(pack_repo["pack"], "rev-parse", "HEAD") == stored["local_commit"]
    finally:
        monkeypatch.delenv("AGENTBASE_SKILL_PACK", raising=False)
        skill_registry.load_active_pack()


def test_manual_update_refreshes_status(monkeypatch):
    """用户手动更新成功后要立刻刷新状态，不能继续显示「有新提交」。"""
    import types

    import agentbase.api.cron as cron

    calls = []
    monkeypatch.setattr(
        cron, "_capture_output", lambda fn, *a, **k: {"ok": True, "output": "updated"}
    )
    monkeypatch.setattr(
        "agentbase.bootstrap.check_skill_pack_sync_once",
        lambda: calls.append(True),
    )

    result = cron.api_update_skills(types.SimpleNamespace(headers={}))

    assert result["ok"] is True
    assert calls, "手动更新后没有刷新 skill pack 状态"


def test_doctor_surfaces_pack_status(pack_repo):
    from agentbase import doctor
    from agentbase.post_install.skills import save_skill_pack_status

    save_skill_pack_status({
        "pack": "trade-business-pack",
        "path": "/packs/trade-business-pack",
        "local_commit": "1111111111111111",
        "remote_commit": "2222222222222222",
        "upstream": "origin/main",
        "behind": 2,
        "status": "update_available",
        "error": "",
        "checked_at": "2026-11-06T12:30:00",
    })

    results = doctor.check_skill_pack_sync()

    assert len(results) == 1
    assert results[0].name == "技能包更新"
    assert results[0].status == doctor.STATUS_WARN
    assert "2 个新提交" in results[0].detail
    assert "手动" in results[0].detail and "git pull" in results[0].detail


def test_doctor_reports_never_checked(pack_repo):
    from agentbase import doctor

    results = doctor.check_skill_pack_sync()

    assert results[0].name == "技能包更新"
    assert results[0].status == doctor.STATUS_WARN
    assert "尚未检查" in results[0].detail


def test_doctor_run_doctor_includes_pack_status(monkeypatch):
    """run_doctor 的快检也要带上「技能包更新」这一项。"""
    from agentbase import doctor

    seen = []
    monkeypatch.setattr(doctor, "check_skill_pack_sync", lambda: seen.append(True) or [])
    monkeypatch.setattr(doctor, "check_hermes_runtime", lambda: [])
    monkeypatch.setattr(doctor, "check_estop", lambda: [])
    monkeypatch.setattr(doctor, "check_post_install", lambda: [])

    doctor.run_doctor(deep=False)

    assert seen, "run_doctor 没有调用 check_skill_pack_sync"
