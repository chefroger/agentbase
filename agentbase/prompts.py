"""
AgentBase — Prompt File Loader.

Unified loader for all user-editable prompt files:
  - ~/.agentbase/prompts/system.md          (全局自定义 system prompt)
  - ~/.agentbase/workspaces/{slug}/agent_identity.md  (工作区级 identity)

读取优先级（纵向覆盖）：
  1. ~/.agentbase/workspaces/{slug}/agent_identity.md   ← 工作区级（最高）
  2. ~/.agentbase/prompts/system.md                   ← 全局用户自定义
  3. 代码 fallback (agentbase/prompt.py)              ← 最低

mtime 缓存：文件未变更时不重复读磁盘。

用户可通过 Web UI 或直接 vim 编辑这些文件，
下次请求自动生效（无需重启服务）。
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from agentbase.prompt import AGENTBASE_SYSTEM_PROMPT_FIRST_TURN as _CODE_FALLBACK

# ─────────────────────────────────────────────────────────────────────────────
# mtime 缓存：{绝对路径: (mtime, 内容)}
# ─────────────────────────────────────────────────────────────────────────────

_FILE_CACHE: dict[str, tuple[float, str]] = {}
_cache_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# 内部 helpers
# ─────────────────────────────────────────────────────────────────────────────


def get_agent_home() -> Path:
    """返回用户 AgentBase 数据目录。

    优先级：AGENT_HOME 环境变量 → 平台默认路径。
    macOS/Linux: ~/.agentbase/, Windows: %LOCALAPPDATA%\agentbase\
    """
    val = os.environ.get("AGENT_HOME", "").strip()
    # 如果环境变量有值，优先使用环境变量指定的路径
    if val:
        return Path(val)
    # Windows 平台：使用 %LOCALAPPDATA%\agentbase\ 作为数据目录
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local_appdata) / "agentbase"
    # macOS / Linux 平台：使用 ~/.agentbase/ 作为默认数据目录
    return Path.home() / ".agentbase"


def _load_file(path: Path, fallback: str = "") -> str:
    """加载文件，启用 mtime 缓存。

    - 文件不存在 → 返回 fallback
    - mtime 未变   → 返回缓存内容
    - mtime 已变   → 重新读磁盘，更新缓存
    """
    # 文件不存在时直接返回 fallback，不进行缓存操作
    if not path.is_file():
        return fallback

    try:
        mtime = path.stat().st_mtime
    except OSError:
        # 读取文件状态失败（如权限不足），安全返回 fallback
        return fallback

    cache_key = str(path.resolve())
    with _cache_lock:
        cached = _FILE_CACHE.get(cache_key)
        # mtime 未变化时直接返回缓存内容，避免重复磁盘 I/O
        if cached is not None and cached[0] == mtime:
            return cached[1]

    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        # 读取文件内容失败（如文件被删除或权限变更），返回 fallback
        return fallback

    with _cache_lock:
        _FILE_CACHE[cache_key] = (mtime, content)
    return content


def _workspace_identity_path(slug: str) -> Path:
    """返回工作区级 identity 文件的绝对路径。

    必须与工作目录布局一致 —— _ensure_data_dir 把 .agentbase-template 复制到
    {data_dir}/workspaces/{slug}/（data_dir 即 ~/.agentbase/{slug}/），文件名是模板里的
    连字符 agent-identity.md：
        ~/.agentbase/{slug}/workspaces/{slug}/agent-identity.md
    历史上这里写作 ~/.agentbase/workspaces/{slug}/agent_identity.md（下划线 + 少一层），
    导致读取方永远读不到 onboarding / 模板写入的文件，「文件优先」整层失效。
    """
    return get_agent_home() / slug / "workspaces" / slug / "agent-identity.md"


def _system_prompt_path() -> Path:
    """返回全局 system prompt 文件的绝对路径。"""
    return get_agent_home() / "prompts" / "system.md"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def get_system_prompt(workspace_slug: str | None = None) -> str:
    """返回 system prompt（纵向覆盖，取最高优先级）。

    优先级：
      1. ~/.agentbase/workspaces/{slug}/agent_identity.md   ← 工作区级
      2. ~/.agentbase/prompts/system.md                    ← 全局
      3. 代码 fallback (AGENTBASE_SYSTEM_PROMPT)           ← 默认

    用户 vim 直接改文件 → mtime 变化 → 下次请求自动读到新内容。
    """
    # 最高优先：工作区级 identity — 如果传入了 workspace_slug，先尝试读取工作区级文件
    if workspace_slug:
        workspace_path = _workspace_identity_path(workspace_slug)
        content = _load_file(workspace_path)
        # 工作区级文件存在且非空，以工作区级 identity 为准
        if content:
            return content

    # 全局自定义 — 工作区级没有命中，尝试读取全局 system.md
    global_path = _system_prompt_path()
    content = _load_file(global_path)
    # 全局文件存在且非空，以全局 prompt 为准
    if content:
        return content

    # 最终 fallback：代码里的默认值，没有任何用户自定义文件时使用
    return _CODE_FALLBACK


def get_agent_identity_by_slug(workspace_slug: str) -> str:
    """根据 workspace_slug 获取 identity 文件内容。

    规范路径优先（{data_dir}/workspaces/{slug}/agent-identity.md）；
    没有内容时回退读历史遗留路径（~/.agentbase/workspaces/{slug}/agent_identity.md）——
    统一路径之前读取方曾指向那里，用户可能已手动编辑过，直接弃用会让改动凭空消失。
    两者都没有时返回空字符串（由调用方决定是否 fallback）。
    """
    content = _load_file(_workspace_identity_path(workspace_slug))
    if content:
        return content
    return _load_file(_legacy_identity_path(workspace_slug))


def _legacy_identity_path(slug: str) -> Path:
    """历史遗留的 identity 文件路径（仅用于兼容读取，不用于写入）。

    路径约定统一前的读取方指向：~/.agentbase/workspaces/{slug}/agent_identity.md
    （下划线、且少一层 workspaces/{slug}）。
    """
    return get_agent_home() / "workspaces" / slug / "agent_identity.md"


def write_agent_identity(workspace_slug: str, content: str) -> None:
    """写入工作区 identity 文件（供 onboarding 或手动编辑调用）。

    文件路径：~/.agentbase/{slug}/workspaces/{slug}/agent-identity.md
    写入后自动失效 mtime 缓存。

    注意：此函数只写文件，不写 DB。
          DB 缓存逻辑由调用方负责。
    """
    path = _workspace_identity_path(workspace_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    # 失效缓存 — 确保下次读取时重新从磁盘加载最新内容
    cache_key = str(path.resolve())
    _FILE_CACHE.pop(cache_key, None)


def write_system_prompt(content: str) -> None:
    """写入全局 system prompt 文件。

    文件路径：~/.agentbase/prompts/system.md
    """
    path = _system_prompt_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    cache_key = str(path.resolve())
    _FILE_CACHE.pop(cache_key, None)


def _brand_safety_path(slug: str) -> Path:
    """返回工作区级品牌安全护栏文件路径。

    与身份文件同约定（工作目录/模板布局）：
        ~/.agentbase/{slug}/workspaces/{slug}/brand_safety.md
    """
    return get_agent_home() / slug / "workspaces" / slug / "brand_safety.md"


def get_brand_safety(workspace_slug: str | None = None) -> str:
    """加载品牌安全护栏文本。

    优先级：
      1. ~/.agentbase/workspaces/{slug}/brand_safety.md（工作区级自定义）
      2. 代码内置 BRAND_SAFETY_BLOCK（全局默认）

    利用现有 mtime 缓存机制，文件修改后下次请求自动生效。
    """
    from agentbase.prompt import BRAND_SAFETY_BLOCK

    if workspace_slug:
        path = _brand_safety_path(workspace_slug)
        content = _load_file(path)
        if content:
            return content
    return BRAND_SAFETY_BLOCK


def _build_workspace_context_block(workspace_id: int | None) -> str:
    """生成"当前 agentbase 会话上下文"段；workspace_id 为 None 时返回空串。

    这段**目前不直接被 resolve_system_prompt 使用** —— 实际注入点放在 agentbase.helpers.build_query
    里，紧跟在它已有的"## 当前工作区"段后面（"ID 是 X / 数据操作必须限定在该工作区" 后面），
    让 LLM 在看到 ID 数字**紧接着**看到"带 workspace_id 参数的工具必须用这个数字"，**强绑定**。

    为什么必须显式写出 workspace_id 数字：chat_memory_list 等工作区隔离工具要 workspace_id
    参数（chat_memory 的 conversations 表按 workspace_id 严格隔离，搜错会读到别人的数据），
    而 LLM 自身没有"当前会话是哪个工作区"的可靠来源 —— 没有这段就只能瞎填。

    返回空串时（workspace_id=None），agentbase.helpers 会**不追加**这段；这与它的
    "降级场景（chat_memory_list 不可用）"行为一致（见 agentbase.hermes_compat.hermes_python_compat）。
    """
    if workspace_id is None:
        return ""
    from agentbase import business_config

    term = business_config.workspace_term()
    return (
        f"\n- **任何带 `workspace_id` 参数的 agentbase 工具**（如 `chat_memory_list`）"
        f"**必须**传这个数字 {workspace_id} —— 这是当前会话的{term}，**不是**用户消息里能取的值。"
    )


def resolve_system_prompt(
    workspace_slug: str | None = None,
    db_identity: str | None = None,
    *,
    code_fallback: str | None = None,
) -> str:
    """组合出最终 system prompt：**基础规则块 + 用户自定义文本**。

    基础规则块（Disclaimer / Role / Language Policy / Data Isolation / 准确规则，
    由 code_fallback 指定档位）始终发送，工作区身份文本追加在其后。
    历史上这里是二选一的优先级链（文件 → DB → 全局 → 代码），而 onboarding 必然写入
    身份文本，于是身份把基础规则整体顶替 —— 实测返回长度恰好等于身份文本长度，
    这些规则从未到达过模型。

    自定义层优先级（高到低）：
      1. 工作区 identity 文件 ~/.agentbase/{slug}/workspaces/{slug}/agent-identity.md
      2. DB agent_identity_md 字段（运行时缓存）
      3. 全局 system.md（~/.agentbase/prompts/system.md）
    三者都没有时只返回基础规则块。

    Args:
        workspace_slug: 工作区 slug（用于定位 identity 文件）
        db_identity:  DB 中 agent_identity_md 字段值（缓存）
        code_fallback: 基础规则块档位（None 时用默认 AGENTBASE_SYSTEM_PROMPT_FIRST_TURN）。
                       OSINT 类 skill 传 AGENTBASE_SYSTEM_PROMPT_OSINT，
                       非首轮传 AGENTBASE_SYSTEM_PROMPT_MINIMAL，
                       文档类任务传 AGENTBASE_SYSTEM_PROMPT_FULL。
    """
    base = code_fallback or _CODE_FALLBACK
    custom = _resolve_custom_prompt(workspace_slug, db_identity)
    # 自定义文本追加在基础规则之后；没有自定义时就是纯基础规则块
    return f"{base}\n\n{custom}" if custom else base


def _resolve_custom_prompt(workspace_slug: str | None, db_identity: str | None) -> str:
    """按优先级取用户自定义身份文本；都没有时返回空串。"""
    # 1. 工作区 identity 文件优先级最高
    if workspace_slug:
        file_content = get_agent_identity_by_slug(workspace_slug)
        if file_content:
            return file_content

    # 2. DB 缓存（onboarding / 前端在线编辑写入）
    if db_identity:
        return db_identity

    # 3. 全局自定义 system.md（用户直接编辑的文件，优先级高于业务配置）
    global_text = _load_file(_system_prompt_path())
    if global_text:
        return global_text

    # 4. business.yaml 的 prompt_overrides.system（业务配置化覆盖）
    try:
        from agentbase import business_config

        business_text = business_config.prompt_override_system()
        if business_text:
            return business_text
    except Exception:
        pass

    # 5. skill pack 的 prompt_overrides.system（包内文件）
    return _pack_prompt_override()


def _pack_prompt_override() -> str:
    """读取当前 skill pack 的 `prompt_overrides.system` 文件内容；没有则空串。"""
    try:
        from agentbase.skill_registry import active_skill_pack, pack_manifest

        raw = (pack_manifest().get("prompt_overrides") or {}).get("system")
        pack = active_skill_pack()
        if not raw or pack is None:
            return ""
        path = Path(raw)
        if not path.is_absolute():
            path = pack / path
        return _load_file(path)
    except Exception:
        return ""


def _doc_task_skills() -> frozenset:
    """文档处理类技能：只有这些任务才需要注入 FULL 的文档生成/分析指南。

    由 skill pack 的 pack.yaml 的 `doc_task_skills` 声明 —— 框架不该知道任何
    具体业务 skill 的名字。没有配置包时返回空集（= 不注入 FULL 提示词）。
    """
    try:
        from agentbase.skill_registry import pack_manifest

        raw = pack_manifest().get("doc_task_skills")
    except Exception:
        return frozenset()
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(x) for x in raw if isinstance(x, str))


def needs_full_prompt(
    matched_name: str | None = None,
    library_id: int | None = None,
    explicit_paths: list[str] | None = None,
) -> bool:
    """是否需要注入 FULL 提示词（22674 字符 ≈ 5700 token，含文档生成指南与文档分析协议）。

    判定为文档处理类任务（任一命中即可）：
      1. 命中文档相关技能
      2. 用户选定了文档库
      3. 用户问题里点名了具体文件/目录

    普通问答（营销/背调/闲聊）不注入，避免每次多付约 5700 token。
    """
    if matched_name and matched_name in _doc_task_skills():
        return True
    if library_id:
        return True
    if explicit_paths:
        return True
    return False


def invalidate_cache(path: Path | str | None = None) -> None:
    """手动失效 mtime 缓存。

    Args:
        path: 失效特定文件，或 None（全部失效）
    """
    # 不传 path 时清空整个缓存，适用于全局重载
    if path is None:
        with _cache_lock:
            _FILE_CACHE.clear()
        return
    key = str(Path(path).resolve())
    with _cache_lock:
        _FILE_CACHE.pop(key, None)
