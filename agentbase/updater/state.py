"""更新状态与互斥锁。

`update-state.json` 的 `phase` 是"半升级"判定的唯一依据：
  backup | updating | verifying | done | rolled_back

只有 `done` / `rolled_back` 是终态；其它值说明更新没走完，
服务启动时必须恢复（见 `recover_if_needed`）。
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

PHASE_BACKUP = "backup"
PHASE_UPDATING = "updating"
PHASE_VERIFYING = "verifying"
PHASE_DONE = "done"
PHASE_ROLLED_BACK = "rolled_back"
PHASES = {PHASE_BACKUP, PHASE_UPDATING, PHASE_VERIFYING, PHASE_DONE, PHASE_ROLLED_BACK}
TERMINAL_PHASES = {PHASE_DONE, PHASE_ROLLED_BACK}


def _agent_home() -> Path:
    raw = os.environ.get("AGENT_HOME", "").strip()
    if raw:
        return Path(raw)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local) / "agentbase"
    return Path.home() / ".agentbase"


def data_dir() -> Path:
    return _agent_home() / "data"


def state_path() -> Path:
    return data_dir() / "update-state.json"


def lock_path() -> Path:
    return data_dir() / "update.lock"


def backups_dir() -> Path:
    return data_dir() / "backups"


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    if os.name != "nt":
        tmp.chmod(0o600)
    os.replace(tmp, path)


def read_state() -> dict:
    try:
        data = json.loads(state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(phase: str, **fields) -> dict:
    """原子写状态（0600）。未知 phase 直接拒绝，避免把半升级写歪。"""
    if phase not in PHASES:
        raise ValueError(f"unknown update phase: {phase!r}")
    data = read_state()
    data.update(fields)
    data["phase"] = phase
    data["updated_at"] = datetime.now(UTC).isoformat()
    _write_private(state_path(), json.dumps(data, ensure_ascii=False, indent=2))
    return data


def is_half_upgraded() -> bool:
    state = read_state()
    phase = state.get("phase")
    return bool(phase) and phase not in TERMINAL_PHASES


# ── 锁 ───────────────────────────────────────────────────────────────────────


def acquire_lock() -> bool:
    """O_EXCL 抢锁。成功返回 True；锁已存在且持有者仍存活返回 False。

    持有者已死（崩溃残留）→ 清掉旧锁再抢。
    """
    path = lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if lock_holder_alive():
        return False
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        lock_path().unlink(missing_ok=True)
    except OSError:
        pass


def lock_holder_alive() -> bool:
    """锁文件存在且其 PID 仍活着 → True。"""
    try:
        pid = int(lock_path().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    from agentbase.process import pid_alive

    return pid_alive(pid)
