"""Phase 7 服务化：自启偏好、停止服务、系统端点、打包入口命令。

不碰真实 launchd / schtasks：外部命令全部 mock。
"""

from __future__ import annotations

import os
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def agent_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return tmp_path


class TestAutostartPreference:
    def test_defaults_to_allowed(self, agent_home):
        from agentbase.service import autostart_preference

        assert autostart_preference() is True

    def test_roundtrip(self, agent_home):
        from agentbase.service import _set_preference, autostart_preference

        _set_preference(False)
        assert autostart_preference() is False
        _set_preference(True)
        assert autostart_preference() is True

    def test_reset(self, agent_home):
        from agentbase.service import (
            _pref_file,
            _set_preference,
            autostart_preference,
            reset_autostart_preference,
        )

        _set_preference(False)
        reset_autostart_preference()
        assert not _pref_file().exists()
        assert autostart_preference() is True

    def test_corrupt_file_falls_back_to_allowed(self, agent_home):
        from agentbase.service import _pref_file, autostart_preference

        _pref_file().parent.mkdir(parents=True, exist_ok=True)
        _pref_file().write_text("not json", encoding="utf-8")
        assert autostart_preference() is True

    def test_successful_toggle_persists_preference(self, agent_home, monkeypatch):
        from agentbase import service

        monkeypatch.setattr(service.sys, "platform", "linux")
        monkeypatch.setattr(service, "_set_autostart_linux", lambda enabled: (True, "ok"))

        ok, _ = service.set_autostart(False)
        assert ok and service.autostart_preference() is False


class TestStopService:
    def test_stops_pid_from_file(self, agent_home, monkeypatch):
        from agentbase import service

        pid = os.getpid()
        service.pid_file().parent.mkdir(parents=True, exist_ok=True)
        service.pid_file().write_text(str(pid), encoding="utf-8")

        killed = []
        monkeypatch.setattr(service.os, "kill", lambda p, sig: killed.append((p, sig)))
        # 第一轮认为还活着，之后认为已退出
        state = {"alive": True}

        def fake_alive(pid):
            alive = state["alive"]
            state["alive"] = False
            return alive

        monkeypatch.setattr(service, "_pid_alive", fake_alive)

        assert service.stop_service(timeout=1) is True
        assert killed == [(pid, service.signal.SIGTERM)]
        assert not service.pid_file().exists()

    def test_reports_not_running_when_no_pid(self, agent_home, monkeypatch):
        from agentbase import opener, service

        monkeypatch.setattr(opener, "is_server_up", lambda *a, **k: False)
        assert service.stop_service() is True


@pytest.fixture
def system_client(monkeypatch):
    from agentbase.api import deps
    from agentbase.app import _create_system_router

    deps.set_session_token("test-token")
    app = FastAPI()
    app.include_router(_create_system_router(), prefix="/api/agentbase")
    client = TestClient(app)
    return client, deps


class TestSystemEndpoints:
    def test_service_status(self, system_client, monkeypatch):
        client, _ = system_client
        from agentbase import opener, service

        monkeypatch.setattr(opener, "is_server_up", lambda *a, **k: True)
        monkeypatch.setattr(service, "autostart_enabled", lambda: False)

        r = client.get(
            "/api/agentbase/system/service-status",
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True, "running": True, "autostart": False}

    def test_autostart_requires_token(self, system_client):
        client, _ = system_client
        r = client.post("/api/agentbase/system/autostart", json={"enabled": True})
        assert r.status_code == 401

    def test_autostart_toggle(self, system_client, monkeypatch):
        client, _ = system_client
        from agentbase import service

        seen = []
        monkeypatch.setattr(service, "set_autostart", lambda enabled: seen.append(enabled) or (True, "ok"))

        r = client.post(
            "/api/agentbase/system/autostart",
            json={"enabled": False},
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert seen == [False]

    def test_autostart_failure_surfaces_error(self, system_client, monkeypatch):
        client, _ = system_client
        from agentbase import service

        monkeypatch.setattr(service, "set_autostart", lambda enabled: (False, "no plist"))

        r = client.post(
            "/api/agentbase/system/autostart",
            json={"enabled": True},
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.json() == {"ok": False, "error": "no plist"}

    def test_quit_returns_before_exiting(self, system_client, monkeypatch):
        client, _ = system_client
        from agentbase import service

        called = []
        monkeypatch.setattr(service, "quit_service", lambda: called.append(True))

        r = client.post(
            "/api/agentbase/system/quit",
            headers={"X-Hermes-Session-Token": "test-token"},
        )

        assert r.status_code == 200
        assert r.json()["ok"] is True
        time.sleep(0.7)  # 后台线程里的 0.5s 延时
        assert called == [True]


class TestPackagedServiceCommand:
    def test_frozen_uses_self_with_service_flag(self, monkeypatch):
        import sys

        from agentbase import opener

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/tmp/frozen", raising=False)

        assert opener._service_command() == [sys.executable, "--service"]

    def test_source_uses_server_script(self, monkeypatch):
        import sys

        from agentbase import opener

        monkeypatch.delattr(sys, "frozen", raising=False)
        cmd = opener._service_command()
        assert cmd is not None
        assert cmd[0] == sys.executable
        assert cmd[-1] == "--no-browser"


class TestAutostartConsent:
    """任务书 §12 红线：安装时不得偷偷注册开机自启。"""

    def test_shell_installer_asks_and_defaults_to_no(self):
        from pathlib import Path

        text = (Path(__file__).resolve().parent.parent / "scripts" / "install.sh").read_text(encoding="utf-8")
        assert "是否开启开机自启" in text, "安装脚本没有询问用户"
        assert "_want_autostart" in text
        assert "[ -t 0 ]" in text, "非交互安装必须走默认分支"
        # 非交互分支返回 1 = 不开启
        block = text.split("_want_autostart() {", 1)[1].split("\n}", 1)[0]
        assert "return 1" in block

    def test_powershell_installer_asks_and_defaults_to_no_without_console(self):
        from pathlib import Path

        text = (Path(__file__).resolve().parent.parent / "scripts" / "install.ps1").read_text(encoding="utf-8")
        assert "是否开启开机自启" in text
        assert "Read-Host" in text
        assert "$WantAutostart = $false" in text  # catch 分支（无控制台）默认关闭

    def test_settings_ui_calls_prefixed_system_endpoints(self):
        """api() **不会**自动补 /api/agentbase 前缀；设置页路径写错会静默 404。"""
        from pathlib import Path

        text = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text(encoding="utf-8")
        for ep in ("/api/agentbase/system/service-status",
                   "/api/agentbase/system/autostart",
                   "/api/agentbase/system/quit"):
            assert ep in text, f"设置页缺少 {ep}"
        assert "api('GET', '/system/" not in text
        assert "api('POST', '/system/" not in text

    def test_legacy_pyinstaller_spec_removed(self):
        """旧 trade 拷贝来的 pyinstaller.spec 必须删除（产品名含 Foreign、死引用一堆）。"""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        assert not (root / "pyinstaller.spec").exists()
        # 正主是 desktop-*.spec
        for name in ("desktop-mac.spec", "desktop-windows.spec", "desktop-linux.spec"):
            assert (root / name).is_file()


class TestSpecHygiene:
    """spec 不能引用已删除的模块（PyInstaller 会静默忽略，打包后才炸）。"""

    def test_specs_do_not_reference_removed_modules(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        for name in ("desktop-mac.spec", "desktop-windows.spec", "desktop-linux.spec"):
            text = (root / name).read_text(encoding="utf-8")
            for stale in ("agentbase.osint", "agentbase.api.customers",
                          "agentbase.api.libraries", "agentbase.api.orders",
                          "webview.platforms", "ai.smarttrade.desktop"):
                assert stale not in text, f"{name} 仍引用已删除/已改名的 {stale}"
            assert "vendor/hermes" in text, f"{name} 未把 vendor/hermes 打进产物"
