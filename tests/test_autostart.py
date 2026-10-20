"""开机自启开关必须可逆：关闭删除注册项后，再次开启要能重建。"""

from __future__ import annotations

import os
import plistlib
import subprocess

import pytest


@pytest.mark.skipif(os.name == "nt", reason="launchd 仅 macOS")
def test_macos_recreates_missing_plist(tmp_path, monkeypatch):
    from agentbase import service

    plist = tmp_path / "com.agentbase.assistant.plist"
    calls: list[tuple] = []
    monkeypatch.setattr(service, "_launch_agent_plist", lambda: plist)
    monkeypatch.setattr(service, "_agent_home", lambda: tmp_path)
    monkeypatch.setattr(
        service, "_launchctl",
        lambda *a: calls.append(a) or subprocess.CompletedProcess(a, 0, b"", b""),
    )

    ok, _ = service._set_autostart_macos(True)

    assert ok
    data = plistlib.loads(plist.read_bytes())
    assert data["Label"] == service.AUTOSTART_LABEL
    assert data["ProgramArguments"]
    assert any(call[0] == "bootstrap" for call in calls)


def test_linux_recreates_missing_unit(tmp_path, monkeypatch):
    from agentbase import service

    unit = tmp_path / "agentbase.service"
    monkeypatch.setattr(service, "_systemd_unit", lambda: unit)
    monkeypatch.setattr(service, "_agent_home", lambda: tmp_path)
    monkeypatch.setattr(
        service.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, b"", b""),
    )

    ok, _ = service._set_autostart_linux(True)

    assert ok
    text = unit.read_text(encoding="utf-8")
    assert "ExecStart=" in text
    assert "[Install]" in text


def test_windows_enable_creates_task_directly(monkeypatch):
    """偏好为 false 时也要真的建计划任务，不能靠 ensure_windows_setup 跳过。"""
    from agentbase import service
    import agentbase.post_install.win_setup as win

    created: list[str] = []
    monkeypatch.setattr(win, "agentbase_dir_from_module", lambda: "dir")
    monkeypatch.setattr(
        win, "ensure_launcher_scripts", lambda d: {"autostart_vbs": "vbs-path"},
    )
    monkeypatch.setattr(
        win, "ensure_scheduled_task",
        lambda vbs: created.append(vbs) or "✓ 已创建计划任务",
    )

    ok, _ = service._set_autostart_windows(True)

    assert ok
    assert created == ["vbs-path"]
