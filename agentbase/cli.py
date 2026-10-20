"""命令行入口（打包内的 console script 目标）。

为什么需要这个模块：`[project.scripts]` 原先指向仓库根的 `server:main`，
而 `packages.find` 只收 `agentbase` 包 —— 顶层模块不被打包，pip 安装后
`agentbase` 命令直接 `ModuleNotFoundError: No module named 'server'`。

这里把「启动序列 + FastAPI 启动」收进包内，console script 只依赖 `agentbase.*`。
（`python server.py` 这条文档路径仍然可用，见仓库根的 server.py。）
"""

from __future__ import annotations


def run_server() -> None:
    """`agentbase` 命令入口：先跑启动序列，再进入 FastAPI 应用。

    启动序列（agentbase.bootstrap.setup）负责：日志过滤、sys.path 调整（让 AgentBase 的
    agentbase 包优先于 Hermes 的同名包）、子命令分发、架构与 Hermes 版本检查、
    .env 加载、YOLO 模式、skills 同步、数据库初始化。**不能跳过**。
    """
    from agentbase.bootstrap import setup

    # 必须先 setup() 再 import app：半升级恢复在 setup() 里执行。
    # 若新版本 app.py 本身无法 import，提前导入会让进程直接退出，
    # 恢复代码永远没有机会跑。
    setup()

    from agentbase.app import main as _app_main

    _app_main()
