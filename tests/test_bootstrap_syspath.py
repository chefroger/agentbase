"""bootstrap._adjust_sys_path 的 Hermes checkout 解析测试。

历史 bug：函数把 `HERMES_HOME` 本身当成 Hermes checkout 插进 sys.path。但
HERMES_HOME 是**数据根目录**（~/.hermes），checkout 在其下的 `hermes-agent/`。
而 `~/.local/bin/agentbase` 包装脚本恰好 `export HERMES_HOME=/Users/.../.hermes`，
于是插进去的是数据根目录（里面没有 hermes_cli）。

这个缺陷长期被掩盖：venv 的 site-packages 里另有一份 hermes-agent 兜底。
2026-09-28 清理掉那份冗余副本后，聊天立刻报「AI Agent 模块未加载」。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase import bootstrap


def _make_checkout(root: Path) -> Path:
    """在 root 下造一个含 hermes_cli 包的假 checkout。"""
    pkg = root / "hermes_cli"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text('__version__ = "0.21.4"\n', encoding="utf-8")
    return root


@pytest.fixture
def isolated(monkeypatch):
    """隔离 sys.path 与 sys.modules，避免测试互相污染。"""
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.delitem(sys.modules, "hermes_cli", raising=False)
    return monkeypatch


class TestHermesCheckoutResolution:
    """vendored 模式（任务书 v2 §10.7）：`vendor/hermes/` 是唯一来源。

    旧实现允许从 `HERMES_HOME` 或 `~/.hermes/hermes-agent` 解析 checkout。
    vendored 之后这条路被**有意封死** —— 用户机器上可能装着独立 Hermes / OpenClaw，
    混用会串数据。这些测试钉住的是「新架构下必须成立的不变量」，不是旧行为。
    """

    def test_resolves_repo_vendored_checkout(self, isolated):
        """默认解析到仓库根的 vendor/hermes/。"""
        isolated.delenv("AGENTBASE_HERMES_CHECKOUT", raising=False)
        checkout = bootstrap._resolve_hermes_checkout()
        assert checkout, "应能解析到 vendor/hermes"
        assert checkout.replace("\\", "/").endswith("vendor/hermes"), checkout
        assert (Path(checkout) / "hermes_cli").is_dir()

    def test_env_override_wins(self, isolated, tmp_path):
        """AGENTBASE_HERMES_CHECKOUT 可覆盖（开发 / 调试用）。"""
        custom = _make_checkout(tmp_path / "custom")
        isolated.setenv("AGENTBASE_HERMES_CHECKOUT", str(custom))

        assert bootstrap._resolve_hermes_checkout() == str(custom)

    def test_invalid_override_falls_back_to_repo_vendor(self, isolated, tmp_path):
        """覆盖路径不是有效 checkout 时，回退到仓库内置的 vendor/hermes。"""
        isolated.setenv("AGENTBASE_HERMES_CHECKOUT", str(tmp_path / "nope"))

        checkout = bootstrap._resolve_hermes_checkout()
        assert checkout.replace("\\", "/").endswith("vendor/hermes")

    def test_adjust_sys_path_inserts_vendored_checkout_before_site_packages(self, isolated):
        """checkout 必须排在 site-packages 之前，否则同名包会遮蔽它。"""
        isolated.delenv("AGENTBASE_HERMES_CHECKOUT", raising=False)
        bootstrap._adjust_sys_path()

        checkout = bootstrap._resolve_hermes_checkout()
        assert checkout in sys.path
        site_indexes = [i for i, p in enumerate(sys.path) if p.endswith("site-packages")]
        if site_indexes:
            assert sys.path.index(checkout) < min(site_indexes), \
                "checkout 排在 site-packages 之后，会被同名包遮蔽"

    def test_never_inserts_user_hermes_home(self, isolated, tmp_path):
        """HERMES_HOME 指向用户自己的 ~/.hermes checkout 时，绝不能被采用。"""
        fake = _make_checkout(tmp_path / "home" / ".hermes" / "hermes-agent")
        isolated.setenv("HERMES_HOME", str(fake))
        isolated.delenv("AGENTBASE_HERMES_CHECKOUT", raising=False)

        bootstrap._adjust_sys_path()

        assert str(fake) not in sys.path, "vendored Hermes 绝不能混用用户的 ~/.hermes"

    def test_hermes_home_is_forced_to_agent_home(self, isolated, tmp_path):
        """HERMES_HOME 必须被强制改成 AGENT_HOME（永不指向 ~/.hermes）。"""
        isolated.setenv("AGENT_HOME", str(tmp_path / "ab"))
        isolated.setenv("HERMES_HOME", str(tmp_path / "user-hermes"))

        bootstrap._adjust_sys_path()

        assert os.environ["HERMES_HOME"] == str(tmp_path / "ab"), (
            "继承来的 HERMES_HOME 必须被覆盖为 AGENT_HOME，否则会串到用户自己的 Hermes 数据"
        )

    def test_agent_home_defaults_to_dot_agentbase(self, isolated, tmp_path):
        """未设 AGENT_HOME 时默认 ~/.agentbase（测试里伪造 home）。"""
        isolated.delenv("AGENT_HOME", raising=False)
        isolated.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))

        bootstrap._adjust_sys_path()

        assert os.environ["HERMES_HOME"] == str(tmp_path / "home" / ".agentbase")


class TestHermesActivationRestore:
    """Hermes 的 pm 激活之后，必须把 Trade 自己的 site-packages 补回 sys.path。

    这是「Trade 跑在 Python 3.14 + 最新 Hermes」整条路线成立的前提：
    `pm/environments.py:activate_dependencies()` 会在 `import hermes_bootstrap` 时
    **按目录名剥掉进程原有的全部 site-packages**，Trade 的依赖（pymupdf / holehe /
    openpyxl …）会全部消失，编译包还因 cp314/3.13 ABI 不符直接崩。不补回来的话，
    Trade 会在运行到文档解析时才炸 —— 而且现场是一串 `ModuleNotFoundError` 天书。
    """

    def test_restores_trade_site_packages_after_activation(self, isolated):
        """激活剥离后必须补回，且补在末尾（让 Hermes 的依赖优先胜出版本冲突）。"""
        import types

        agentbase_site = bootstrap._trade_site_packages()
        assert agentbase_site, "测试环境应能解析出 site-packages 目录"

        original_path = list(sys.path)
        original_pythonpath = os.environ.get("PYTHONPATH", "")
        # 造一个假的 hermes_bootstrap：导入它的副作用就是「激活」——剥离 site-packages。
        # 放进 sys.modules 后 `import hermes_bootstrap` 直接命中，不会真的执行 import。
        sys.modules["hermes_bootstrap"] = types.ModuleType("hermes_bootstrap")
        sys.path[:] = [
            p for p in sys.path if not p.endswith(("site-packages", "dist-packages"))
        ]
        try:
            bootstrap._activate_hermes_env_and_restore_trade_paths()

            assert agentbase_site in sys.path, "激活后未把 Trade 的 site-packages 补回 sys.path"
            # 必须在末尾：一旦两侧版本漂移，让 Hermes 的托管代际优先，避免 Trade 的
            # 老 pin 把 Hermes 需要的版本压下去
            assert sys.path[-1] == agentbase_site
            # PYTHONPATH 被激活覆盖过，也必须补回 —— 否则 Trade 起的子进程
            # （如走 holehe 的 OSINT Layer 1）找不到 Trade 的依赖
            assert agentbase_site in os.environ.get("PYTHONPATH", "")
        finally:
            sys.path[:] = original_path
            sys.modules.pop("hermes_bootstrap", None)
            if original_pythonpath:
                os.environ["PYTHONPATH"] = original_pythonpath
            else:
                os.environ.pop("PYTHONPATH", None)

    def test_missing_hermes_does_not_raise(self, isolated, monkeypatch):
        """Hermes 未安装时不得抛异常：降级模式下这条路也会被走到。"""
        import builtins

        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "hermes_bootstrap":
                raise ImportError("no hermes here")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fake_import)

        # 不抛异常即通过
        bootstrap._activate_hermes_env_and_restore_trade_paths()

    def test_restore_works_when_hermes_bootstrap_already_cached(self, isolated):
        """`hermes_bootstrap` 已缓存时，恢复**仍然**必须生效。

        这是审查提出的隐含假设（ⓐ）：函数靠 `import hermes_bootstrap` 的副作用触发激活，
        而模块已在 `sys.modules` 时那次 import 是**空操作**、没有任何副作用。
        但恢复段是**无条件**执行的，所以「缓存 → 无副作用」不该影响恢复结果。
        钉住它：否则未来有人把恢复改成「只在真的发生了激活时才补」，就会在
        「同一个进程里第二次调用」时静默不补 —— 而那正是界面只显示
        「AI Agent 模块未加载」那种现场的成因。
        """
        import types

        agentbase_site = bootstrap._trade_site_packages()
        assert agentbase_site, "测试环境应能解析出 site-packages 目录"

        original_path = list(sys.path)
        original_pythonpath = os.environ.get("PYTHONPATH", "")
        # 已缓存的假模块：**没有任何副作用**（不剥离 sys.path）
        sys.modules["hermes_bootstrap"] = types.ModuleType("hermes_bootstrap")
        # 主动把 Trade 的 site-packages 拿掉，模拟「别处已经剥离过」
        sys.path[:] = [
            p for p in sys.path if not p.endswith(("site-packages", "dist-packages"))
        ]
        try:
            bootstrap._activate_hermes_env_and_restore_trade_paths()

            assert agentbase_site in sys.path, (
                "hermes_bootstrap 已缓存（import 无副作用）时，恢复段被跳过了 —— "
                "它必须无条件执行"
            )
            assert sys.path[-1] == agentbase_site
        finally:
            sys.path[:] = original_path
            sys.modules.pop("hermes_bootstrap", None)
            if original_pythonpath:
                os.environ["PYTHONPATH"] = original_pythonpath
            else:
                os.environ.pop("PYTHONPATH", None)

    def test_unresolvable_site_packages_is_loud(self, isolated, monkeypatch, capsys):
        """解析不到 Trade 自己的 site-packages 时**必须响亮报错**，不能静默继续。

        这是 ⓐ 真正会「静默降级」的那条路径：`_trade_site_packages()` 返回空串时，
        补齐与 PYTHONPATH 修补**双双跳过** —— 进程表面还能跑，实际只剩 Hermes 的依赖。
        原来的实现一声不响，用户看到的是运行到文档解析时的一串 ModuleNotFoundError。
        """
        import types

        monkeypatch.setattr(bootstrap, "_trade_site_packages", lambda: "")
        sys.modules["hermes_bootstrap"] = types.ModuleType("hermes_bootstrap")
        try:
            bootstrap._activate_hermes_env_and_restore_trade_paths()
        finally:
            sys.modules.pop("hermes_bootstrap", None)

        out = capsys.readouterr().out
        assert "无法解析 Trade 自身的 site-packages" in out, (
            "静默降级路径必须留下可追踪的输出，否则现场无从排查"
        )
