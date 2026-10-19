"""跨平台进程存活检查。

**不要用 ``os.kill(pid, 0)`` 判活**：Windows 上 ``CTRL_C_EVENT`` 的值就是 0，
``os.kill`` 会把它当成 ``GenerateConsoleCtrlEvent``，可能把 Ctrl+C 发给整个
控制台进程组（CI 里表现为莫名其妙的 KeyboardInterrupt）。psutil 是硬依赖，
直接用它。
"""

from __future__ import annotations

import os


def pid_alive(pid: int) -> bool:
    """进程是否存在；``pid <= 0`` 一律视为不存在（防止误杀进程组）。"""
    if pid <= 0:
        return False
    try:
        import psutil
    except ImportError:  # pragma: no cover - psutil 在 requirements.txt 里是硬依赖
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    return psutil.pid_exists(pid)
