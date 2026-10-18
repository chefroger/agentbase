"""自身更新机制（任务书 §12）：状态、锁、changelog、更新源、半升级、端点。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def agent_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return tmp_path


class TestState:
    def test_roundtrip(self, agent_home):
        from agentbase.updater import state

        state.write_state(state.PHASE_UPDATING, source="git", old_head="abc")
        data = state.read_state()
        assert data["phase"] == "updating"
        assert data["source"] == "git"
        assert data["old_head"] == "abc"

    def test_file_is_private(self, agent_home):
        from agentbase.updater import state

        state.write_state(state.PHASE_DONE)
        mode = state.state_path().stat().st_mode & 0o777
        if os.name != "nt":
            assert mode == 0o600

    def test_unknown_phase_rejected(self, agent_home):
        from agentbase.updater import state

        with pytest.raises(ValueError):
            state.write_state("half-way")

    @pytest.mark.parametrize("phase,expected", [
        ("backup", True), ("updating", True), ("verifying", True),
        ("done", False), ("rolled_back", False), ("", False),
    ])
    def test_half_upgraded(self, agent_home, phase, expected):
        from agentbase.updater import state

        if phase:
            state.write_state(phase)
        assert state.is_half_upgraded() is expected


class TestLock:
    def test_acquire_release(self, agent_home):
        from agentbase.updater import state

        assert state.acquire_lock() is True
        assert state.lock_holder_alive() is True
        assert state.acquire_lock() is False  # 自己持锁时不可重入
        state.release_lock()
        assert state.lock_holder_alive() is False

    def test_stale_lock_is_reclaimed(self, agent_home):
        from agentbase.updater import state

        state.lock_path().parent.mkdir(parents=True, exist_ok=True)
        state.lock_path().write_text("999999999", encoding="utf-8")
        assert state.acquire_lock() is True
        state.release_lock()


class TestChangelog:
    def test_parse_groups_versions(self):
        from agentbase.updater import changelog

        text = (
            "# Changelog\n\n## [1.2.0] - 2026-10-18\n- 新功能 A\n- 修复 B\n\n"
            "## [1.1.0] - 2026-10-01\n- 老功能\n"
        )
        entries = changelog.parse(text)
        assert [e["version"] for e in entries] == ["1.2.0", "1.1.0"]
        assert entries[0]["lines"] == ["新功能 A", "修复 B"]

    def test_render_uses_range(self, tmp_path, monkeypatch):
        from agentbase.updater import changelog

        changelog_file = tmp_path / "CHANGELOG.md"
        changelog_file.write_text(
            "## [1.3.0] - 2026-10-18\n- 三\n## [1.2.0] - 2026-10-01\n- 二\n"
            "## [1.1.0] - 2026-09-01\n- 一\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(changelog, "changelog_path", lambda: changelog_file)

        notes = changelog.render("1.1.0", "1.3.0")
        assert "三" in notes and "二" in notes
        assert "一" not in notes

    def test_fallback_when_missing(self, tmp_path, monkeypatch):
        from agentbase.updater import changelog

        monkeypatch.setattr(changelog, "changelog_path", lambda: None)
        assert changelog.render("1.0.0", "2.0.0") == changelog.FALLBACK


class TestPackageSource:
    def _make_release(self, tmp_path: Path, content: bytes = b"new-binary"):
        exe = tmp_path / "AgentBase"
        exe.write_bytes(b"old-binary")
        artifact = tmp_path / "AgentBase.new"
        artifact.write_bytes(content)
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "version": "9.9.9",
            "url": artifact.name,
            "sha256": hashlib.sha256(content).hexdigest(),
        }), encoding="utf-8")
        return exe, manifest

    def test_prepare_replaces_and_rollback_restores(self, tmp_path):
        from agentbase.updater.sources import PackageSource

        exe, manifest = self._make_release(tmp_path)
        src = PackageSource(executable=str(exe), manifest=str(manifest))

        src.prepare()
        assert exe.read_bytes() == b"new-binary"
        assert (tmp_path / "AgentBase.old").read_bytes() == b"old-binary"

        src.rollback(src.snapshot())
        assert exe.read_bytes() == b"old-binary"

    def test_checksum_mismatch_keeps_old(self, tmp_path):
        from agentbase.updater.sources import PackageSource

        exe, manifest = self._make_release(tmp_path)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["sha256"] = "0" * 64
        manifest.write_text(json.dumps(data), encoding="utf-8")

        src = PackageSource(executable=str(exe), manifest=str(manifest))
        with pytest.raises(RuntimeError):
            src.prepare()
        assert exe.read_bytes() == b"old-binary"

    def test_missing_manifest_is_actionable(self, tmp_path):
        from agentbase.updater.sources import PackageSource

        src = PackageSource(executable=str(tmp_path / "AgentBase"), manifest="")
        with pytest.raises(RuntimeError) as exc:
            src.prepare()
        assert "manifest" in str(exc.value)


class TestGitSourceRollback:
    def test_snapshot_records_missing_repo(self, tmp_path):
        from agentbase.updater.sources import GitSource

        src = GitSource(tmp_path / "missing")
        snap = src.snapshot()
        assert snap == {"old_head": "", "repo_existed": False}

    def test_rollback_removes_repo_created_by_update(self, tmp_path):
        """更新前没有安装目录 → 本次 clone 出来的目录删掉就是回滚。"""
        from agentbase.updater.sources import GitSource

        repo = tmp_path / "agentbase"
        repo.mkdir()
        (repo / "server.py").write_text("new", encoding="utf-8")

        src = GitSource(repo)
        src.rollback({"old_head": "", "repo_existed": False})
        assert not repo.exists()

    def test_rollback_without_head_raises_when_repo_existed(self, tmp_path):
        from agentbase.updater.sources import GitSource

        repo = tmp_path / "agentbase"
        repo.mkdir()
        src = GitSource(repo)
        with pytest.raises(RuntimeError):
            src.rollback({"old_head": "", "repo_existed": True})


class TestEngineRequest:
    def test_request_update_records_service_cmd(self, agent_home, monkeypatch):
        import sys

        from agentbase.updater import engine, state

        class FakeSource:
            name = "git"

            def snapshot(self):
                return {"old_head": "", "repo_existed": False}

        monkeypatch.setattr(engine, "detect_source", lambda: FakeSource())
        monkeypatch.setattr(engine, "spawn_detached_updater", lambda: True)

        result = engine.request_update()

        assert result["ok"] is True
        saved = state.read_state()
        assert saved["service_cmd"][0] == sys.executable
        assert saved["phase"] == state.PHASE_UPDATING

    def test_request_update_rolls_back_state_when_spawn_fails(self, agent_home, monkeypatch):
        from agentbase.updater import engine, state

        class FakeSource:
            name = "git"

            def snapshot(self):
                return {}

        monkeypatch.setattr(engine, "detect_source", lambda: FakeSource())
        monkeypatch.setattr(engine, "spawn_detached_updater", lambda: False)

        result = engine.request_update()

        assert result["ok"] is False
        assert state.read_state()["phase"] == state.PHASE_ROLLED_BACK


class TestEngineRecovery:
    def test_terminal_state_is_noop(self, agent_home):
        from agentbase.updater import engine, state

        state.write_state(state.PHASE_DONE)
        assert engine.recover_if_needed() is False

    def test_alive_updater_blocks_service_start(self, agent_home, monkeypatch):
        from agentbase.updater import engine, state

        state.write_state(state.PHASE_UPDATING)
        monkeypatch.setattr(state, "lock_holder_alive", lambda: True)
        assert engine.recover_if_needed() is True

    def test_alive_verifying_lets_new_service_start(self, agent_home, monkeypatch):
        from agentbase.updater import engine, state

        state.write_state(state.PHASE_VERIFYING)
        monkeypatch.setattr(state, "lock_holder_alive", lambda: True)
        assert engine.recover_if_needed() is False

    def test_dead_lock_spawns_recovery(self, agent_home, monkeypatch):
        from agentbase.updater import engine, state

        state.write_state(state.PHASE_UPDATING)
        monkeypatch.setattr(state, "lock_holder_alive", lambda: False)
        spawned = []
        monkeypatch.setattr(engine, "_spawn_recovery", lambda: spawned.append(True) or True)

        assert engine.recover_if_needed() is True
        assert spawned == [True]

    def test_wait_escalates_to_sigkill(self, agent_home, monkeypatch):
        from agentbase.updater import engine

        signals = []

        class FakeTime:
            def __init__(self): self.t = 0.0

            def monotonic(self): return self.t

            def sleep(self, seconds):
                self.t += seconds

        fake = FakeTime()
        monkeypatch.setattr(engine, "time", fake)
        monkeypatch.setattr(engine, "_service_pid", lambda: 4242)
        monkeypatch.setattr(engine, "_pid_alive", lambda pid: True)
        monkeypatch.setattr(engine.os, "kill", lambda pid, sig: signals.append(sig))

        engine.wait_for_service_exit(timeout=1.0, grace=1.0)
        assert engine.signal.SIGTERM in signals
        assert engine.signal.SIGKILL in signals


@pytest.fixture
def system_client():
    from agentbase.api import deps
    from agentbase.app import _create_system_router

    deps.set_session_token("test-token")
    app = FastAPI()
    app.include_router(_create_system_router(), prefix="/api/agentbase")
    return TestClient(app)


class TestSystemEndpoints:
    def test_update_uses_detached_engine(self, system_client, monkeypatch):
        from agentbase import app as app_mod

        seen = []

        def fake_request_update():
            seen.append(True)
            return {"ok": True, "message": "更新已开始"}

        monkeypatch.setattr("agentbase.updater.request_update", fake_request_update)
        monkeypatch.setattr(app_mod, "_perform_restart", lambda: seen.append("restart"))
        # 后台任务会真的发 SIGTERM 退出当前进程 —— 测试里必须拦住
        monkeypatch.setattr("agentbase.service.quit_service", lambda: seen.append("quit"))

        r = system_client.post(
            "/api/agentbase/system/update",
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert seen[0] is True, "更新请求必须走独立更新器，不能在服务进程内执行"
        assert "restart" not in seen, "更新不应走旧的就地重启路径"
        assert "quit" in seen, "派发更新器后服务必须退出"

    def test_changelog_endpoint(self, system_client, monkeypatch):
        from agentbase.updater import changelog

        monkeypatch.setattr(changelog, "render", lambda current, latest: "· 新功能")

        r = system_client.get(
            "/api/agentbase/system/changelog?latest=9.9.9",
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.status_code == 200
        assert r.json()["notes"] == "· 新功能"
