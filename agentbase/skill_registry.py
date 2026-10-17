"""
AgentBase — Skill 注册表（**加载器 + 查询 API，不含任何业务数据**）。

框架自身不定义任何 skill。注册表内容全部来自当前激活的 **skill pack**：

    ~/.agentbase/business.yaml 的 skill_pack 字段
      → 包的 pack.yaml 的 registry 字段（默认 registry.yaml）
      → 该文件里的 skills / blocked_skills

**没有配置 skill pack（或包加载失败）时注册表为空** —— 框架照常启动、聊天可用，
只是不加载任何业务技能，前端提示"未加载业务技能"。这是刻意设计的降级路径，
不是错误状态。

本模块在 L4 层，不 import 任何 agentbase 内部模块。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# 注册表（由 load_active_pack() 就地填充）
# ─────────────────────────────────────────────────────────────────────────────
# 每个 entry 包含:
#   name      : skill 标识符（对应 SKILL.md 目录名）
#   triggers  : 触发关键词/短语列表（OR 匹配，大小写不敏感）
#   aliases   : 同义 skill 名
#   input_fmt : 用户应提供什么（自然语言描述）
#   output_fmt: 用户会得到什么（自然语言描述）
#   augment_prompt: (DEPRECATED fallback) 硬编码注入文本，
#                   新 skill 优先使用 SKILL.md frontmatter 的 injection_prompt
#
# ⚠️ **必须就地修改 `_SKILLS`，不能重新绑定**：skill_router.py 在模块层
#    `from agentbase.skill_registry import _SKILLS`，拿到的是列表对象引用；
#    重新绑定会让它永远停留在旧列表上。见 load_active_pack()。
_SKILLS: list[dict] = []

# 禁用的 skill：系统不触发这些技能，仅保留为引用记录。由 pack 提供。
_BLOCKED_SKILLS: frozenset = frozenset()

# 注册表版本号：每次 load_active_pack() 自增。
# 消费方（skill_router 的预编译正则、semantic 索引）据此判断是否需要重建 ——
# 注册表是运行时从 skill pack 加载的，模块 import 时可能是空的。
REGISTRY_VERSION = 0


# ─────────────────────────────────────────────────────────────────────────────
# Skill pack 解析与加载
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_REGISTRY_FILE = "registry.yaml"


def agent_home() -> Path:
    """AgentBase 数据根目录（AGENT_HOME 优先，默认 ~/.agentbase）。"""
    raw = os.environ.get("AGENT_HOME", "").strip()
    return Path(raw) if raw else Path.home() / ".agentbase"


def repo_root() -> Path:
    """框架仓库根（skill_pack 相对路径的解析基准）。"""
    return Path(__file__).resolve().parent.parent


def active_skill_pack() -> Path | None:
    """解析当前激活的 skill pack 目录。

    优先级：
      1. `AGENTBASE_SKILL_PACK` 环境变量（测试与开发用）
      2. `{AGENT_HOME}/business.yaml` 的 `skill_pack` 字段
         （相对路径按仓库根解析）

    任一环节缺失或读不出内容 → None（= 不加载任何业务技能）。
    """
    env = os.environ.get("AGENTBASE_SKILL_PACK", "").strip()
    if env:
        return Path(env).expanduser()

    cfg = agent_home() / "business.yaml"
    if not cfg.is_file():
        return None

    data = _read_yaml(cfg)
    if not isinstance(data, dict):
        return None
    raw = str(data.get("skill_pack") or "").strip()
    if not raw:
        return None

    p = Path(raw).expanduser()
    return p if p.is_absolute() else repo_root() / p


def pack_manifest(pack_dir: Path | None = None) -> dict:
    """当前 skill pack 的 pack.yaml 内容（无包 / 读不出时返回空 dict）。

    框架用它读包级配置 —— 比如 `doc_task_skills`（哪些 skill 需要注入 FULL 提示词）。
    这样框架不必知道任何具体的业务 skill 名字。
    """
    target = pack_dir if pack_dir is not None else active_skill_pack()
    if target is None:
        return {}
    data = _read_yaml(target / "pack.yaml")
    return data if isinstance(data, dict) else {}


def load_pack(pack_dir: Path | None) -> tuple[list[dict], frozenset]:
    """从一个 skill pack 目录读出 (skills, blocked_skills)。

    **任何失败都降级为空注册表**，不抛异常 —— 包缺失/写坏不该让框架起不来。
    """
    if pack_dir is None or not pack_dir.is_dir():
        return [], frozenset()

    registry_name = DEFAULT_REGISTRY_FILE
    manifest = _read_yaml(pack_dir / "pack.yaml")
    if isinstance(manifest, dict) and manifest.get("registry"):
        registry_name = str(manifest["registry"])

    data = _read_yaml(pack_dir / registry_name)
    if not isinstance(data, dict):
        return [], frozenset()

    raw_skills = data.get("skills")
    skills = [
        s for s in raw_skills
        if isinstance(s, dict) and isinstance(s.get("name"), str) and s["name"]
    ] if isinstance(raw_skills, list) else []

    raw_blocked = data.get("blocked_skills")
    blocked = frozenset(
        str(x) for x in raw_blocked if isinstance(x, (str, int))
    ) if isinstance(raw_blocked, list) else frozenset()

    return skills, blocked


def load_active_pack() -> int:
    """按 business.yaml 重新加载注册表，返回加载到的 skill 数。"""
    global _BLOCKED_SKILLS, REGISTRY_VERSION
    skills, blocked = load_pack(active_skill_pack())
    _SKILLS[:] = skills          # 就地修改 —— 见文件顶部说明
    _BLOCKED_SKILLS = blocked
    REGISTRY_VERSION += 1        # 让消费方重建缓存
    return len(skills)


def _read_yaml(path: Path) -> Any:
    """读 YAML；文件不存在或解析失败都返回 None（不抛）。"""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        return yaml.safe_load(content)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 预编译正则（import 时一次性构建，避免每次匹配都编译）
# ─────────────────────────────────────────────────────────────────────────────

# 显式 skill 调用模式："用 skill 名" 或 "load skill skill 名"
_EXPLICIT_RE = re.compile(
    r'(?:用|使用|调用|加载|load?\s*(?:skill)?)\s*(?P<skill>[\w\u4e00-\u9fff-]+)',
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Public query API（仅数据查询，不包含匹配逻辑）
# ─────────────────────────────────────────────────────────────────────────────

def list_skills() -> list[dict]:
    """返回所有注册的 skill 条目（不含 augment_prompt，减少 token）。"""
    return [
        {k: v for k, v in s.items() if k != "augment_prompt"}
        for s in _SKILLS
    ]


def skill_names() -> list[str]:
    """返回所有注册 skill 的名称列表。"""
    return [s["name"] for s in _SKILLS]


def get_skill_by_name(name: str) -> dict | None:
    """按名称查找 skill（用于显式 skill= 参数调用）。"""
    for s in _SKILLS:
        if s["name"] == name:
            return s
    return None


# import 时按 business.yaml 加载一次。没有配置包 → 空注册表（正常降级）。
load_active_pack()
