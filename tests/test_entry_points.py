"""命令行入口的打包正确性测试。

历史缺陷：`[project.scripts]` 里 `agentbase = server:main`、`desktop = desktop:main`
指向**仓库根的顶层模块**，而 `packages.find` 只收 `agentbase` 包、也没有声明 `py-modules`
→ 任何 pip 安装后这两个命令都是 `ModuleNotFoundError`（实测 `~/.agentbase/venv/bin/agentbase`
报 `No module named 'server'`）。

另外 `server.py` 原先在**模块顶层**执行 `setup(); main()`，意味着
`from server import main` 会顺带启动整个服务 —— 作为 console script 目标尤其危险。
"""

from __future__ import annotations

import pathlib
import sys
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


class TestConsoleScriptPackaging:
    """[project.scripts] 的目标必须真的能被安装解析。"""

    def test_script_modules_are_packaged(self):
        """包内模块要存在；顶层模块必须在 py-modules 里声明。"""
        data = _pyproject()
        scripts = data["project"].get("scripts", {})
        py_modules = set(data.get("tool", {}).get("setuptools", {}).get("py-modules", []))

        assert scripts, "应当声明 console scripts"
        for name, target in scripts.items():
            module = target.split(":", 1)[0]
            if "." in module:
                # 包内模块（如 agentbase.post_install）→ 源码树里必须存在
                rel = module.replace(".", "/")
                exists = (ROOT / f"{rel}.py").is_file() or (ROOT / rel / "__init__.py").is_file()
                assert exists, f"{name} → {module} 在源码树里不存在"
            else:
                assert module in py_modules, (
                    f"{name} 指向顶层模块 {module}，但未在 py-modules 中声明 "
                    f"→ pip 安装后该命令会 ModuleNotFoundError"
                )


class TestServerModuleHasNoSideEffects:
    """import server 不得启动服务。"""

    def test_import_does_not_run_startup(self, monkeypatch):
        calls: list[str] = []
        from agentbase import app as app_mod
        from agentbase import bootstrap as bs

        monkeypatch.setattr(bs, "setup", lambda *a, **k: calls.append("setup"))
        monkeypatch.setattr(app_mod, "main", lambda *a, **k: calls.append("main"))
        sys.modules.pop("server", None)

        import server  # noqa: F401

        assert calls == [], f"import server 触发了副作用：{calls}（应放在 __main__ 守卫内）"


class TestRunServerEntryPoint:
    """console script 入口必须跑完整启动序列（setup → app.main）。"""

    def test_run_server_calls_setup_then_app_main(self, monkeypatch):
        calls: list[str] = []
        from agentbase import app as app_mod
        from agentbase import bootstrap as bs
        from agentbase import cli

        monkeypatch.setattr(bs, "setup", lambda *a, **k: calls.append("setup"))
        monkeypatch.setattr(app_mod, "main", lambda *a, **k: calls.append("app.main"))

        cli.run_server()

        assert calls == ["setup", "app.main"], (
            "必须先跑 bootstrap.setup()（sys.path/版本检查/skills/数据库），再进 app.main()"
        )

    def test_setup_runs_before_app_import(self, monkeypatch):
        """app 无法 import 时，setup()（含半升级恢复）必须已经执行。"""
        from agentbase import bootstrap as bs
        from agentbase import cli

        calls: list[str] = []
        monkeypatch.setattr(bs, "setup", lambda *a, **k: calls.append("setup"))
        monkeypatch.setitem(sys.modules, "agentbase.app", None)

        with pytest.raises(ImportError):
            cli.run_server()

        assert calls == ["setup"]

    def test_server_run_setup_before_app_import(self, monkeypatch):
        sys.modules.pop("server", None)
        import server

        calls: list[str] = []
        monkeypatch.setattr(server, "setup", lambda: calls.append("setup"))
        monkeypatch.setitem(sys.modules, "agentbase.app", None)

        with pytest.raises(ImportError):
            server.run()

        assert calls == ["setup"]
