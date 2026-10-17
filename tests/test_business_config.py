"""business.yaml 配置化：默认值、文件覆盖、品牌、onboarding 字段、工作目录、prompt 覆盖。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase import business_config  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_config(monkeypatch, tmp_path):
    """每个用例一个独立的 AGENT_HOME，避免读到真实 ~/.agentbase/business.yaml。"""
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    business_config.reload()
    yield tmp_path
    business_config.reload()


def _write(home: Path, text: str) -> None:
    (home / "business.yaml").write_text(text, encoding="utf-8")
    business_config.reload()


def test_defaults_without_file(_isolated_config):
    cfg = business_config.load()
    assert cfg["business_name"] == "AgentBase"
    assert cfg["branding"]["title"] == "AgentBase"
    assert cfg["work_dirs"] == [{"name": "documents", "description": "业务文档"}]
    assert business_config.onboarding_fields()


def test_file_overrides_branding(_isolated_config):
    _write(_isolated_config, """
business_name: "示例业务"
tagline: "一句话"
branding:
  title: "示例助手"
  welcome: "你好呀"
""")
    assert business_config.branding()["title"] == "示例助手"
    assert business_config.branding()["welcome"] == "你好呀"
    # 没写的 logo 保留默认空串
    assert business_config.branding()["logo"] == ""


def test_partial_branding_keeps_defaults(_isolated_config):
    _write(_isolated_config, "branding:\n  title: X\n")
    b = business_config.branding()
    assert b["title"] == "X"
    assert b["welcome"]  # 默认欢迎语没被清掉


def test_onboarding_fields_from_file(_isolated_config):
    _write(_isolated_config, """
onboarding_fields:
  - key: role
    label: "助手角色"
    example: "AI 销售助手"
  - key: products
    label: "产品"
    example: "电机"
""")
    fields = business_config.onboarding_fields()
    assert [f["key"] for f in fields] == ["role", "products"]
    assert fields[1]["label"] == "产品"


def test_empty_onboarding_fields_falls_back(_isolated_config):
    _write(_isolated_config, "onboarding_fields: []\n")
    assert business_config.onboarding_fields()  # 空列表不生效，回落默认


def test_work_dirs_drive_generated_directories(_isolated_config):
    _write(_isolated_config, """
work_dirs:
  - name: docs
    description: "文档"
  - name: assets
    description: "素材"
""")
    assert business_config.work_dir_names() == ["docs", "assets"]

    from agentbase.workspace import workdir

    assert [c for c, _ in workdir._WORK_DIR_CATEGORIES] == ["docs", "assets"]


def test_prompt_override(_isolated_config):
    assert business_config.prompt_override_system() == ""
    _write(_isolated_config, 'prompt_overrides:\n  system: "你是测试助手"\n')
    assert business_config.prompt_override_system() == "你是测试助手"


def test_branding_endpoint_reads_config(_isolated_config):
    _write(_isolated_config, 'branding:\n  title: "示例助手"\n  welcome: "你好"\nbusiness_name: "示例业务"\n')

    from agentbase.api.branding import get_branding

    data = get_branding()
    assert data["title"] == "示例助手"
    assert data["welcome"] == "你好"
    assert data["business_name"] == "示例业务"


def test_onboarding_identity_uses_configured_fields(_isolated_config):
    _write(_isolated_config, """
onboarding_fields:
  - key: role
    label: "助手角色"
    example: "AI 销售助手"
  - key: products
    label: "产品/服务"
    example: "电机"
""")

    from agentbase.onboarding import _build_agent_identity

    text = _build_agent_identity("Acme", {"role": "销售助手", "products": "电机"})
    assert "助手角色" in text and "销售助手" in text
    assert "产品/服务" in text and "电机" in text
    # 未配置的字段不应出现
    assert "目标客户" not in text


def test_ensure_business_config_copies_template_once(_isolated_config):
    repo_root = Path(__file__).resolve().parent.parent
    target = business_config.ensure_business_config(repo_root)
    assert target.is_file()
    assert "business_name" in target.read_text(encoding="utf-8")

    # 用户改过之后，绝不能被模板覆盖
    target.write_text("business_name: 用户自己的\n", encoding="utf-8")
    business_config.ensure_business_config(repo_root)
    assert "用户自己的" in target.read_text(encoding="utf-8")
