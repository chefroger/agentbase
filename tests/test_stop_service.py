"""停止服务失败时不能删掉仍存活进程的 pidfile。"""

from __future__ import annotations


def test_stop_service_keeps_pidfile_when_process_survives(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    import agentbase.service as service

    pid_file = tmp_path / "data" / "agentbase.pid"
    pid_file.parent.mkdir(parents=True)
    pid_file.write_text("123", encoding="utf-8")

    monkeypatch.setattr(service, "read_pid", lambda: 123)
    monkeypatch.setattr(service, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(service.os, "kill", lambda pid, sig: None)

    assert service.stop_service(timeout=0) is False
    assert pid_file.is_file(), "进程仍存活时 pidfile 不能被删除"
