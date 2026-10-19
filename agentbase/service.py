"""常驻服务的管理工具（Phase 7）。

启动/探测/打开界面复用 `agentbase.opener`（`agentbase open` 子命令）——
这个模块只负责 opener 没有的两件事：

- 停止服务（pidfile + SIGTERM）
- 开机自启的查询/切换（用户级；Windows 复用 win_setup 的隐藏式 VBS 方案）

平台自启目标：
- macOS  = ~/Library/LaunchAgents/com.agentbase.assistant.plist
- Windows = 计划任务 "AgentBase"（wscript 隐藏窗口，见 win_setup）
- Linux  = systemd user unit（install.sh 注册的那份）
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

AUTOSTART_LABEL = "com.agentbase.assistant"
WINDOWS_TASK_NAME = "AgentBase"


# ── 路径 ─────────────────────────────────────────────────────────────────────


def _agent_home() -> Path:
    raw = os.environ.get("AGENT_HOME", "").strip()
    if raw:
        return Path(raw)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local) / "agentbase"
    return Path.home() / ".agentbase"


def pid_file() -> Path:
    return _agent_home() / "data" / "agentbase.pid"


def read_pid() -> int | None:
    try:
        return int(pid_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    from agentbase.process import pid_alive

    return pid_alive(pid)


# ── 停止 / 退出 ──────────────────────────────────────────────────────────────


def stop_service(timeout: float = 10.0) -> bool:
    """停止服务：优先 pidfile；没有 pidfile 时视为未运行。"""
    pid = read_pid()
    if pid and _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not _pid_alive(pid):
                break
            time.sleep(0.2)
        try:
            pid_file().unlink(missing_ok=True)
        except OSError:
            pass
        return not _pid_alive(pid)
    from agentbase.opener import is_server_up

    return not is_server_up()


def quit_service() -> None:
    """让当前服务进程退出（供 API 调用；调用方应先返回响应）。"""
    os.kill(os.getpid(), signal.SIGTERM)


# ── 开机自启 ─────────────────────────────────────────────────────────────────


def _launch_agent_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{AUTOSTART_LABEL}.plist"


def _systemd_unit() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "agentbase.service"


def _pref_file() -> Path:
    return _agent_home() / "data" / "autostart.json"


def autostart_preference() -> bool:
    """用户是否允许开机自启（默认允许）。

    为什么需要单独的偏好文件：Windows 每次服务启动都会幂等调用
    `ensure_windows_setup()` 重建计划任务 —— 没有这份记录的话，用户在设置页
    关掉自启，重启服务后它又会被悄悄装回来。
    """
    import json

    try:
        data = json.loads(_pref_file().read_text(encoding="utf-8"))
        return bool(data.get("enabled", True))
    except (OSError, ValueError):
        return True


def _set_preference(enabled: bool) -> None:
    import json

    path = _pref_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"enabled": enabled}), encoding="utf-8")
    except OSError:
        pass


def reset_autostart_preference() -> None:
    """安装/重装时恢复默认（允许自启）。"""
    try:
        _pref_file().unlink(missing_ok=True)
    except OSError:
        pass


def autostart_enabled() -> bool:
    if sys.platform == "darwin":
        return _launch_agent_plist().is_file()
    if os.name == "nt":
        try:
            r = subprocess.run(
                ["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME],
                capture_output=True, timeout=10,
            )
            return r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    return _systemd_unit().is_file()


def set_autostart(enabled: bool) -> tuple[bool, str]:
    """切换开机自启。返回 (ok, message)。

    只操作**用户级**条目，绝不提权；关闭时清掉注册项。
    成功的切换会写入偏好，防止服务重启时把自启悄悄装回来。
    """
    if sys.platform == "darwin":
        ok, msg = _set_autostart_macos(enabled)
    elif os.name == "nt":
        ok, msg = _set_autostart_windows(enabled)
    else:
        ok, msg = _set_autostart_linux(enabled)
    if ok:
        _set_preference(enabled)
    return ok, msg


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, timeout=15)


def _set_autostart_macos(enabled: bool) -> tuple[bool, str]:
    plist = _launch_agent_plist()
    domain = f"gui/{os.getuid()}"
    if enabled:
        if not plist.is_file():
            return False, "开机自启项不存在，请重新运行安装脚本。"
        _launchctl("bootout", domain, str(plist))
        r = _launchctl("bootstrap", domain, str(plist))
        if r.returncode != 0:
            return False, (r.stderr or b"launchctl bootstrap failed").decode(errors="replace")
        return True, "已开启开机自启"
    if not plist.is_file():
        return True, "开机自启本来就是关闭的"
    _launchctl("bootout", domain, str(plist))
    try:
        plist.unlink()
    except OSError as exc:
        return False, f"删除自启项失败：{exc}"
    return True, "已关闭开机自启"


def _set_autostart_windows(enabled: bool) -> tuple[bool, str]:
    if enabled:
        # 复用安装期的隐藏式实现（VBS + 计划任务），避免弹终端窗口。
        try:
            from agentbase.post_install.win_setup import (
                agentbase_dir_from_module,
                ensure_windows_setup,
            )

            messages = ensure_windows_setup(agentbase_dir_from_module())
        except Exception as exc:
            return False, f"开启开机自启失败：{exc}"
        if not any("✓" in m for m in messages):
            return False, "；".join(messages) or "开启开机自启失败"
        return True, "已开启开机自启（登录后隐藏运行）"

    r = subprocess.run(
        ["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"],
        capture_output=True, timeout=15,
    )
    if r.returncode == 0:
        return True, "已关闭开机自启"
    return True, "开机自启本来就是关闭的"


def _set_autostart_linux(enabled: bool) -> tuple[bool, str]:
    unit = _systemd_unit()
    if enabled:
        if not unit.is_file():
            return False, "开机自启项不存在，请重新运行安装脚本。"
        r = subprocess.run(
            ["systemctl", "--user", "enable", "--now", unit.name],
            capture_output=True, timeout=15,
        )
        return (r.returncode == 0,
                "已开启开机自启" if r.returncode == 0
                else (r.stderr or b"systemctl enable failed").decode(errors="replace"))
    if not unit.is_file():
        return True, "开机自启本来就是关闭的"
    subprocess.run(["systemctl", "--user", "disable", "--now", unit.name],
                   capture_output=True, timeout=15)
    try:
        unit.unlink()
    except OSError as exc:
        return False, f"删除自启项失败：{exc}"
    return True, "已关闭开机自启"
