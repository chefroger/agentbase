"""
AgentBase — standalone FastAPI server.

Start:
    python server.py
    python server.py --port 8080

引导逻辑在 agentbase.bootstrap 中，app factory 在 agentbase.app 中。
"""

from agentbase.bootstrap import setup


def run() -> None:
    """完整启动：先跑启动序列，再导入并进入 FastAPI 应用。

    app 必须延迟导入：半升级恢复在 setup() 内执行；若新版本 app.py
    无法 import，提前导入会让进程退出，恢复逻辑永远跑不到。
    """
    setup()
    from agentbase.app import main

    main()


# 必须放在守卫内：本文件在仓库根、未被打包进 pip 包，但历史上被
# console script 当成 `server:main` 的目标 —— 那样单单 `from server import main`
# 就会连带执行整套启动流程（含起服务）。入口已改为 agentbase.cli:run_server。
if __name__ == "__main__":
    run()
