"""
业务配置加载器（`business.yaml`）。

框架本身**不含业务信息**。所有业务相关内容集中到
`~/.agentbase/business.yaml`：

    business_name: "示例业务"
    tagline: "一句话介绍"
    skill_pack: "skill-packs/demo-pack"
    onboarding_fields:
      - key: role
        label: "助手角色"
        example: "AI 销售助手"
    branding:
      title: "示例助手"
      welcome: "你好，我是你的业务助手。"
      logo: "static/logo.png"
    work_dirs:
      - name: documents
        description: "业务文档"
    prompt_overrides:
      system: ""            # 可选：覆盖全局 system prompt 的文本

文件不存在 / 字段缺失时一律走内置默认值 —— **没有业务配置也能启动**。
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CACHE: dict[str, Any] | None = None
_CACHE_KEY: tuple | None = None

DEFAULT_ONBOARDING_FIELDS: list[dict] = [
    {"key": "role", "label": "助手角色", "example": "AI 业务助手"},
    {"key": "products", "label": "产品/服务", "example": "请填写主要产品或服务"},
    {"key": "audience", "label": "目标客户", "example": "请填写目标客户群"},
]

DEFAULT_WORK_DIRS: list[dict] = [
    {"name": "documents", "description": "业务文档"},
]

DEFAULTS: dict[str, Any] = {
    "business_name": "AgentBase",
    "tagline": "",
    "skill_pack": "",
    "onboarding_fields": DEFAULT_ONBOARDING_FIELDS,
    "branding": {
        "title": "AgentBase",
        "welcome": "你好，我是你的业务助手。",
        "logo": "",
    },
    "work_dirs": DEFAULT_WORK_DIRS,
    "prompt_overrides": {"system": ""},
}


def agent_home() -> Path:
    raw = os.environ.get("AGENT_HOME", "").strip()
    return Path(raw) if raw else Path.home() / ".agentbase"


def config_path() -> Path:
    return agent_home() / "business.yaml"


def _read_yaml(path: Path) -> dict:
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, Exception):
        return {}
    return data if isinstance(data, dict) else {}


def _file_key(path: Path) -> tuple | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (str(path), st.st_mtime_ns, st.st_size)


def load() -> dict:
    """返回合并后的业务配置（文件值覆盖默认值）。带 mtime 缓存。"""
    global _CACHE, _CACHE_KEY
    path = config_path()
    key = _file_key(path)
    with _LOCK:
        if _CACHE is not None and key == _CACHE_KEY:
            return _CACHE

        merged: dict[str, Any] = {**DEFAULTS, **(_read_yaml(path) if key else {})}

        # 嵌套字段单独合并，避免文件里只写 branding.title 就丢掉其它默认值
        branding = {**DEFAULTS["branding"], **(merged.get("branding") or {})}
        merged["branding"] = branding
        for name in ("onboarding_fields", "work_dirs"):
            value = merged.get(name)
            if not isinstance(value, list) or not value:
                merged[name] = list(DEFAULTS[name])

        _CACHE = merged
        _CACHE_KEY = key
        return merged


def reload() -> dict:
    """清缓存并重新读取（测试 / 运行时改配置后调用）。

    同时刷新依赖该配置的模块（工作目录分类）。
    """
    global _CACHE, _CACHE_KEY
    with _LOCK:
        _CACHE = None
        _CACHE_KEY = None
    result = load()
    try:
        from agentbase.workspace import workdir

        workdir.reload_work_dirs()
    except Exception:
        pass
    return result


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def branding() -> dict:
    return dict(load()["branding"])


def onboarding_fields() -> list[dict]:
    return list(load()["onboarding_fields"])


def work_dirs() -> list[dict]:
    return list(load()["work_dirs"])


def work_dir_names() -> list[str]:
    return [str(d.get("name", "")).strip() for d in work_dirs() if d.get("name")]


def prompt_override_system() -> str:
    overrides = load().get("prompt_overrides") or {}
    value = overrides.get("system", "")
    return str(value or "").strip()


def ensure_business_config(repo_root: Path | None = None) -> Path:
    """确保 `~/.agentbase/business.yaml` 存在；不存在时从模板复制。

    已存在时**绝不覆盖** —— 用户可能已经填了自己的业务信息。
    返回 business.yaml 的路径。
    """
    target = config_path()
    if target.is_file():
        return target

    root = repo_root or Path(__file__).resolve().parent.parent
    template = root / ".agentbase-template" / "business.yaml"
    if not template.is_file():
        return target  # 没有模板也不报错：框架用内置默认值启动

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return target
