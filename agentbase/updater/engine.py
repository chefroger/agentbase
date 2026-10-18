"""更新器引擎：备份 → 换新版 → 自检 → 完成/回滚。

进程模型（任务书 §12）：
- 服务进程收到更新请求 → `request_update()` 写状态、派生 `update --detached`、退出。
- 更新器进程（独立）→ `run_update()`：等旧服务退出、备份、换新版、起新服务、自检。
- 服务启动早期 → `recover_if_needed()`：半升级判定（见 state.py）。

更新器进程运行的是**旧代码**；换版后必须用子进程/新服务验证新代码，
不能在当前进程里 import 新模块。
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from agentbase.updater import state as update_state
from agentbase.updater.sources import (
    PackageSource,
    UpdateSource,
    detect_source,
)

# 等待旧服务退出的预算（任务书固定：30s SIGTERM，再 5s SIGKILL）
SERVICE_EXIT_TIMEOUT = 30.0
SERVICE_KILL_GRACE = 5.0
# 新服务就绪预算
SERVICE_READY_TIMEOUT = 90.0
BACKUP_KEEP = 5
PORT = 9120


# ── 请求侧（服务进程调用） ───────────────────────────────────────────────────


def request_update() -> dict:
    """写状态并派生独立更新器；调用方随后退出服务。"""
    if update_state.lock_holder_alive():
        return {"ok": False, "error": "已有更新正在进行，请稍后再试。"}

    source = detect_source()
    try:
        snapshot = source.snapshot()
    except Exception:
        snapshot = {}

    # 记录"旧服务怎么启动的"：回滚后用它把原来的服务拉起来。
    # 更新失败时 source.service_command() 可能指向一个已被删除的新目录，
    # 没有这条记录就只能让用户手动重启。
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 and not os.path.isabs(argv0):
        argv0 = os.path.abspath(argv0)
    service_cmd = [sys.executable, argv0, *sys.argv[1:]] if argv0 else []

    update_state.write_state(
        update_state.PHASE_UPDATING,
        source=source.name,
        requested_at=time.time(),
        service_cmd=service_cmd,
        **snapshot,
    )

    if not spawn_detached_updater():
        update_state.write_state(
            update_state.PHASE_ROLLED_BACK,
            error="更新器启动失败",
        )
        return {"ok": False, "error": "更新器启动失败，请查看日志。"}

    return {
        "ok": True,
        "message": "更新已开始，服务即将退出；完成后会自动重新启动。",
    }


def _self_command(*args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    repo = Path(__file__).resolve().parent.parent.parent
    return [sys.executable, str(repo / "server.py"), *args]


def _spawn_detached(cmd: list[str]) -> bool:
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        kwargs["start_new_session"] = True
    log_path = _agent_home() / "logs"
    try:
        log_path.mkdir(parents=True, exist_ok=True)
        log = open(log_path / "updater.log", "ab")
        subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            close_fds=True, **kwargs,
        )
        log.close()
        return True
    except OSError:
        return False


def spawn_detached_updater() -> bool:
    return _spawn_detached(_self_command("update", "--detached"))


def _spawn_recovery() -> bool:
    return _spawn_detached(_self_command("update", "--recover", "--detached"))


def _agent_home() -> Path:
    raw = os.environ.get("AGENT_HOME", "").strip()
    if raw:
        return Path(raw)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local) / "agentbase"
    return Path.home() / ".agentbase"


# ── 更新器主流程 ─────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[updater] {msg}", flush=True)


def run_update() -> dict:
    """更新器进程入口。返回结构化结果（CLI 打印用）。"""
    if not update_state.acquire_lock():
        return {"ok": False, "error": "另一个更新器正在运行"}
    try:
        _log("等待旧服务退出 …")
        wait_for_service_exit()

        source = detect_source()
        _log(f"更新源：{source.name}")

        _log("备份数据 …")
        update_state.write_state(update_state.PHASE_BACKUP, source=source.name)
        backup_path = _backup()
        snapshot = source.snapshot()

        _log("下载/应用新版本 …")
        update_state.write_state(
            update_state.PHASE_UPDATING, source=source.name,
            backup_path=backup_path, **snapshot,
        )
        source.prepare()

        _log("启动新版本并自检 …")
        update_state.write_state(
            update_state.PHASE_VERIFYING, source=source.name,
            backup_path=backup_path, **snapshot,
        )
        ok, detail = _start_and_verify(source)
        if not ok:
            raise RuntimeError(detail)

        if isinstance(source, PackageSource):
            source.cleanup_old_artifact()
        update_state.write_state(
            update_state.PHASE_DONE, source=source.name,
            backup_path=backup_path, verified=True,
        )
        _log("更新完成")
        return {"ok": True, "message": "更新完成", "backup": backup_path}
    except Exception as exc:
        _log(f"更新失败：{exc}；开始回滚")
        return _rollback_and_recover(str(exc))
    finally:
        update_state.release_lock()


def run_recovery() -> dict:
    """半升级恢复：把代码/产物换回 state 记录的上一个版本并启动服务。"""
    if not update_state.acquire_lock():
        return {"ok": False, "error": "另一个更新器正在运行"}
    try:
        wait_for_service_exit()
        saved = update_state.read_state()
        source = detect_source()
        try:
            source.rollback(saved)
            _log("已回滚到上一版本")
        except Exception as exc:
            _log(f"回滚失败：{exc}")
        update_state.write_state(
            update_state.PHASE_ROLLED_BACK, recovered=True,
            error=saved.get("error", ""),
        )
        _start_service(source, _previous_service_cmd(saved))
        return {"ok": True, "message": "已回滚并重新启动"}
    finally:
        update_state.release_lock()


# ── 备份 ─────────────────────────────────────────────────────────────────────


def _backup() -> str:
    from agentbase.post_install.backup import backup_agentbase

    out_dir = update_state.backups_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = backup_agentbase(str(out_dir))
    _prune_backups(out_dir)
    return path


def _prune_backups(directory: Path) -> None:
    files = sorted(
        directory.glob("agentbase-backup-*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[BACKUP_KEEP:]:
        try:
            old.unlink()
        except OSError:
            pass


# ── 服务生命周期 ─────────────────────────────────────────────────────────────


def wait_for_service_exit(
    timeout: float = SERVICE_EXIT_TIMEOUT, grace: float = SERVICE_KILL_GRACE,
) -> None:
    """等旧服务退出；超时 SIGTERM，再超时 SIGKILL（任务书要求）。"""
    pid = _service_pid()
    if not pid or not _pid_alive(pid):
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.2)

    _log(f"旧服务 {timeout:.0f}s 未退出，发送 SIGTERM")
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.2)

    _log("SIGTERM 后仍未退出，发送 SIGKILL")
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    for _ in range(10):
        if not _pid_alive(pid):
            return
        time.sleep(0.2)


def _service_pid() -> int | None:
    try:
        return int((_agent_home() / "data" / "agentbase.pid").read_text().strip())
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _start_service(source: UpdateSource, cmd: list[str] | None = None) -> bool:
    command = cmd or source.service_command(PORT)
    _log(f"启动服务：{' '.join(command)}")
    return _spawn_detached(command)


def _previous_service_cmd(saved: dict) -> list[str] | None:
    """回滚后用原进程的命令行拉起旧服务（state 里由 request_update 写入）。"""
    cmd = saved.get("service_cmd")
    if isinstance(cmd, list) and cmd and all(isinstance(x, str) for x in cmd):
        return cmd
    return None


def _start_and_verify(source: UpdateSource) -> tuple[bool, str]:
    if not _start_service(source):
        return False, "新版本启动失败（进程未能派生）"
    return _wait_ready()


def _wait_ready(timeout: float = SERVICE_READY_TIMEOUT) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "ok":
                    # 新版状态端点带 hermes_usable；缺失时（旧端点）不据此判失败
                    if data.get("hermes_usable") is False:
                        return False, "新版本启动后 Hermes 不可用"
                    return True, ""
        except Exception as exc:
            last = str(exc)
        time.sleep(0.5)
    return False, f"新版本在 {int(timeout)}s 内未就绪：{last}"


def _rollback_and_recover(error: str) -> dict:
    saved = update_state.read_state()
    source = detect_source()
    try:
        # 新服务可能已起但自检失败 —— 先停掉再回滚
        wait_for_service_exit(timeout=5.0, grace=2.0)
        source.rollback(saved)
        _log("回滚成功")
        update_state.write_state(update_state.PHASE_ROLLED_BACK, error=error, recovered=True)
        _start_service(source, _previous_service_cmd(saved))
        return {"ok": False, "error": error, "rolled_back": True}
    except Exception as exc:
        update_state.write_state(
            update_state.PHASE_ROLLED_BACK, error=f"{error}; 回滚失败: {exc}", recovered=False,
        )
        _start_service(source, _previous_service_cmd(saved))
        return {"ok": False, "error": f"{error}; 回滚失败: {exc}", "rolled_back": False}


# ── 启动时的半升级检测 ────────────────────────────────────────────────────────


def recover_if_needed() -> bool:
    """服务启动早期调用。

    返回 True 表示当前进程应**立即退出**（更新器在跑，或已派发恢复）。

    判定：
      - 无 phase / 终态 → 正常启动
      - 锁存活：
          updating/backup → 更新器正在工作，当前服务不该起（退出）
          verifying       → 是更新器启动的新服务，正常启动
      - 锁已死（崩溃残留）→ 半升级，派发恢复更新器并退出
    """
    saved = update_state.read_state()
    phase = saved.get("phase")
    if not phase or phase in update_state.TERMINAL_PHASES:
        return False

    alive = update_state.lock_holder_alive()
    if alive:
        if phase == update_state.PHASE_VERIFYING:
            return False
        _log(f"更新器正在工作（phase={phase}），本次启动退出")
        return True

    _log(f"检测到半升级（phase={phase}），派发恢复")
    if _spawn_recovery():
        return True
    # 派发失败：至少把状态标成终态，避免每次启动都卡在这里
    update_state.write_state(
        update_state.PHASE_ROLLED_BACK, error="恢复进程派发失败", recovered=False,
    )
    return False
