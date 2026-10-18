"""AgentBase 自身更新机制（任务书 §12）。

对外接口：

    from agentbase.updater import request_update, run_update, recover_if_needed

- `request_update()`：服务端调用。写状态、派生独立更新器、返回；调用方随后退出服务。
- `run_update()`：更新器进程调用。备份 → 换新版 → 自检 → 完成/回滚。
- `recover_if_needed()`：服务启动早期调用。检测半升级并按 phase 分流。
"""

from agentbase.updater.engine import (
    recover_if_needed,
    request_update,
    run_recovery,
    run_update,
)

__all__ = ["request_update", "run_update", "run_recovery", "recover_if_needed"]
