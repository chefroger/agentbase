"""AgentBase 启动器（Phase 7 服务化入口）。

三种用法（同一个可执行文件）：

- 双击 / 无参数：确保后台服务在跑，然后用系统浏览器打开 UI。
- `--service`：前台运行常驻服务（无窗口；由自启机制或双击派生）。
- `--stop`：停止服务。

界面复用静态前端，Python 只跑后端，不画窗口（任务书 §12 方案 A）。
"""

import multiprocessing
import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if "--stop" in args:
        from agentbase.service import stop_service

        ok = stop_service()
        print("AgentBase 服务已停止" if ok else "AgentBase 服务未在运行")
        return 0 if ok else 1

    if "--service" in args:
        args.remove("--service")
        # 常驻服务不打开浏览器；UI 由双击入口负责。
        if "--no-browser" not in args:
            args.append("--no-browser")
        sys.argv = [sys.argv[0], *args]
        from agentbase.cli import run_server

        run_server()
        return 0

    # 双击入口：确保服务在跑，再打开 UI（复用 `agentbase open` 的实现）。
    from agentbase.opener import open_agentbase

    result = open_agentbase()
    print(result)
    return 0 if result.startswith("✓") else 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
