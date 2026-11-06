"""设置页 API：Key 写 .env、默认模型写 config、Skill Pack 安装/启用/卸载。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase import business_config  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    business_config.reload()
    yield tmp_path
    business_config.reload()


def test_save_keys_writes_env_0600(_isolated):
    from agentbase.api.settings import KeysPayload, save_keys

    save_keys(KeysPayload(keys={"DEEPSEEK_API_KEY": "sk-test", "OTHER_KEY": "v"}))

    env = _isolated / ".env"
    assert env.is_file()
    text = env.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=sk-test" in text
    assert "OTHER_KEY=v" in text
    if os.name != "nt":  # Windows 不保留 POSIX 权限位
        assert oct(env.stat().st_mode & 0o777) == "0o600"


def test_save_keys_rejects_env_injection(_isolated):
    from fastapi import HTTPException

    from agentbase.api.settings import KeysPayload, save_keys

    with pytest.raises(HTTPException) as exc:
        save_keys(KeysPayload(keys={"PROXY": "1\nHTTPS_PROXY=http://evil"}))

    assert exc.value.status_code == 400
    assert not (_isolated / ".env").exists()


def test_save_keys_rejects_invalid_name(_isolated):
    from fastapi import HTTPException

    from agentbase.api.settings import KeysPayload, save_keys

    with pytest.raises(HTTPException) as exc:
        save_keys(KeysPayload(keys={"bad key": "v"}))

    assert exc.value.status_code == 400


def test_save_keys_preserves_other_lines(_isolated):
    ( _isolated / ".env").write_text("# comment\nKEEP=1\nDEEPSEEK_API_KEY=old\n", encoding="utf-8")

    from agentbase.api.settings import KeysPayload, save_keys

    save_keys(KeysPayload(keys={"DEEPSEEK_API_KEY": "new"}))

    text = (_isolated / ".env").read_text(encoding="utf-8")
    assert "# comment" in text
    assert "KEEP=1" in text
    assert "DEEPSEEK_API_KEY=new" in text


def test_empty_keys_rejected(_isolated):
    from fastapi import HTTPException

    from agentbase.api.settings import KeysPayload, save_keys

    with pytest.raises(HTTPException):
        save_keys(KeysPayload(keys={"X": "  "}))


def test_get_settings_never_returns_key_values(_isolated):
    from agentbase.api.settings import KeysPayload, get_settings, save_keys

    save_keys(KeysPayload(keys={"DEEPSEEK_API_KEY": "sk-secret-value"}))

    blob = str(get_settings())
    assert "sk-secret-value" not in blob


def test_pack_install_activate_remove(_isolated, tmp_path):
    from agentbase.api.packs import (
        ActivatePayload,
        InstallPayload,
        activate_pack,
        install_pack,
        list_packs,
        remove_pack,
    )

    src = tmp_path / "my-pack"
    (src / "skills" / "demo-skill").mkdir(parents=True)
    (src / "pack.yaml").write_text("name: my-pack\nversion: 1\nskills: [demo-skill]\n", encoding="utf-8")
    (src / "skills" / "demo-skill" / "SKILL.md").write_text(
        "---\nname: demo-skill\n---\nbody\n", encoding="utf-8"
    )

    installed = install_pack(InstallPayload(path=str(src)))
    assert installed["name"] == "my-pack"
    assert (_isolated / "skill-packs" / "my-pack" / "pack.yaml").is_file()

    assert any(p["name"] == "my-pack" for p in list_packs()["packs"])

    activated = activate_pack(ActivatePayload(name="my-pack"))
    assert activated["ok"] is True
    assert business_config.get("skill_pack").endswith("my-pack")

    remove_pack("my-pack")
    assert not (_isolated / "skill-packs" / "my-pack").exists()
    assert not business_config.get("skill_pack")


def test_moa_requires_two_configured_providers(_isolated, monkeypatch):
    """少于 2 个已配置 provider 时必须拒绝开启，而不是写一份坏配置。"""
    import types

    from fastapi import HTTPException

    fake_pkg = types.ModuleType("hermes_cli")
    fake_cfg = types.ModuleType("hermes_cli.config")
    fake_cfg.load_config = lambda: {}
    fake_cfg.save_config = lambda *a, **k: None
    fake_moa = types.ModuleType("hermes_cli.moa_config")
    fake_moa.validate_moa_payload = lambda raw: []
    monkeypatch.setitem(sys.modules, "hermes_cli", fake_pkg)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", fake_cfg)
    monkeypatch.setitem(sys.modules, "hermes_cli.moa_config", fake_moa)

    from agentbase import hermes_compat
    monkeypatch.setattr(
        hermes_compat, "list_provider_records",
        lambda: [{"id": "openai", "has_key": True, "models": ["gpt-5"]}],
    )

    from agentbase.api.settings import MoaPayload, set_moa

    with pytest.raises(HTTPException) as exc:
        set_moa(MoaPayload(enabled=True))
    assert exc.value.status_code == 400


def test_pack_name_traversal_rejected(_isolated, tmp_path):
    from fastapi import HTTPException

    from agentbase.api.packs import ActivatePayload, activate_pack

    with pytest.raises(HTTPException):
        activate_pack(ActivatePayload(name="../evil"))


def test_write_env_failure_keeps_original_bytes(_isolated, monkeypatch):
    """写入中途失败：原 .env 必须一字未动，临时文件必须清理。"""
    from agentbase.api import settings

    env = _isolated / ".env"
    original = b"EXISTING=1\n"
    env.write_bytes(original)

    class _FailingOs:
        chmod = staticmethod(os.chmod)

        @staticmethod
        def replace(*args, **kwargs):
            raise OSError("disk full")

    monkeypatch.setattr(settings, "os", _FailingOs)

    with pytest.raises(OSError):
        settings._write_env({"NEW_KEY": "v"})

    assert env.read_bytes() == original
    assert not (_isolated / ".env.tmp").exists(), "失败后临时文件必须清理"


def test_write_env_concurrent_saves_do_not_lose_updates(_isolated, monkeypatch):
    """并发保存必须串行化：两次更新都要落盘，不能互相覆盖或写交错。"""
    import threading
    import time

    from agentbase.api import settings

    env = _isolated / ".env"
    env.write_text("BASE=0\n", encoding="utf-8")

    real_read_text = Path.read_text

    def _slow_read(self, *args, **kwargs):
        text = real_read_text(self, *args, **kwargs)
        if self == env:
            # 放大「读完到写入」的窗口：没有锁时两个线程会同时读到旧内容
            time.sleep(0.05)
        return text

    monkeypatch.setattr(Path, "read_text", _slow_read)

    barrier = threading.Barrier(2)

    def _worker(key):
        barrier.wait()
        settings._write_env({key: "v"})

    threads = [
        threading.Thread(target=_worker, args=(f"KEY_{i}",)) for i in (1, 2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = env.read_text(encoding="utf-8").splitlines()
    assert "BASE=0" in lines
    assert "KEY_1=v" in lines and "KEY_2=v" in lines, "并发保存丢了更新"
    assert all("=" in line for line in lines), ".env 出现交错残行"
