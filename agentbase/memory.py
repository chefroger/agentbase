"""
AgentBase — 记忆桥接层（Hindsight 集成）。

提供 agentbase/chat_memory 与 Hindsight 长期记忆后端之间的轻量桥接。
独立于 Hermes Agent 运行时工作（不需要 MemoryManager）。

当 hindsight-client 已安装并配置时，对话轮次将被自动保留到知识图谱中，
以实现跨会话召回。否则，本模块优雅降级，所有操作变为空操作。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Hindsight 可用性检测 ─────────────────────────────────────────────────────

_hindsight_available: bool | None = None  # 三态：None=尚未检查


def is_available() -> bool:
    """检查 Hindsight 是否已安装并配置。"""
    global _hindsight_available
    # 如果已经检查过，直接返回缓存结果，避免重复导入
    if _hindsight_available is not None:
        return _hindsight_available

    try:
        import importlib
        importlib.import_module("hindsight_client")
        # 检查环境变量中是否有 API 密钥
        has_key = bool(
            os.environ.get("HINDSIGHT_API_KEY", "")
            or os.environ.get("HINDSIGHT_LLM_API_KEY", "")
        )
        # 如果环境变量中没有 API 密钥，则尝试从配置文件中读取
        if not has_key:
            from agentbase.paths import hermes_home
            _hermes_root = hermes_home()
            config_paths = [
                _hermes_root / "hindsight" / "config.json",
                Path.home() / ".hindsight" / "config.json",
            ]
            # 遍历所有可能的配置文件路径
            for p in config_paths:
                # 如果配置文件存在，尝试读取其中的 API 密钥
                if p.exists():
                    try:
                        # 显式 utf-8：配置文件可能含非 ASCII（Windows 默认 cp1252 会读失败）
                        cfg = json.loads(p.read_text(encoding="utf-8"))
                        # 支持多种配置字段名，兼容不同版本
                        if cfg.get("apiKey") or cfg.get("api_key") or cfg.get("mode") == "local_embedded":
                            has_key = True
                            break
                    except Exception:
                        pass
        _hindsight_available = has_key
    except ImportError:
        # 未安装 hindsight_client 包，标记为不可用
        _hindsight_available = False

    return _hindsight_available


def reset_cache() -> None:
    """清空 Hindsight 可用性与客户端缓存。仅供测试或重新配置时使用。"""
    global _hindsight_available, _client
    _hindsight_available = None
    _client = None


# ── 客户端（懒初始化，复用单例）────────────────────────────────────────────

_client: Any = None


def _get_client():
    """返回缓存的 Hindsight 客户端，如果不可用则返回 None。"""
    global _client
    # 如果 Hindsight 整体不可用，直接返回 None
    if not is_available():
        return None
    # 如果客户端已经初始化过，直接返回缓存的实例
    if _client is not None:
        return _client

    try:
        from hermes_constants import get_hermes_home
        from hindsight_client import Hindsight

        api_key = os.environ.get("HINDSIGHT_API_KEY", "")
        api_url = os.environ.get("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io")
        timeout = int(os.environ.get("HINDSIGHT_TIMEOUT", "120"))

        # 尝试从 Hermes profile 作用域的配置文件中读取覆盖值
        config_path = get_hermes_home() / "hindsight" / "config.json"
        # 如果配置文件存在，用其中的值覆盖环境变量（环境变量优先）
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                # 配置文件损坏或不可读时降级为空配置，避免阻断客户端初始化
                logger.warning("Hindsight config 解析失败: %s", exc)
                cfg = {}
            api_key = api_key or cfg.get("apiKey", "") or cfg.get("api_key", "")
            api_url = cfg.get("api_url", api_url)
            timeout = int(cfg.get("timeout", timeout))

        # 如果最终仍没有 API 密钥，则不创建客户端
        if not api_key:
            logger.debug("Hindsight: 未配置 API 密钥，不创建客户端")
            return None

        _client = Hindsight(
            base_url=api_url,
            api_key=api_key,
            timeout=float(timeout),
        )
        logger.info("Hindsight 客户端已连接: %s", api_url)
    except Exception as exc:
        logger.warning("Hindsight 客户端初始化失败: %s", exc)
        _client = None

    return _client


# ── 公开 API ─────────────────────────────────────────────────────────────────

def retain(
    content: str,
    context: str = "",
    *,
    bank_id: str = "agentbase",
    document_id: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    """将信息存储到 Hindsight 长期记忆。

    成功返回 True，如果 Hindsight 不可用则返回 False。
    """
    client = _get_client()
    # 如果 Hindsight 客户端不可用，静默返回 False 表示操作未执行
    if client is None:
        return False

    try:
        metadata = {"source": "agentbase-ai-assistant"}
        kwargs: dict[str, Any] = {
            "bank_id": bank_id,
            "content": content,
            "metadata": metadata,
        }
        # 仅当 context 非空时才添加，避免发送不必要的空字段
        if context:
            kwargs["context"] = context
        # 仅当 document_id 提供时才添加，用于关联特定文档
        if document_id:
            kwargs["document_id"] = document_id
        # 仅当 tags 提供时才添加，便于后续按标签检索
        if tags:
            kwargs["tags"] = tags

        client.retain(**kwargs)
        logger.debug("Hindsight 保留: bank=%s, content_len=%d, context=%s",
                      bank_id, len(content), context or "(无)")
        return True
    except Exception as exc:
        logger.warning("Hindsight 保留失败: %s", exc)
        return False


def recall(
    query: str,
    *,
    bank_id: str = "agentbase",
    budget: str = "mid",
    max_tokens: int = 4096,
) -> str | None:
    """搜索 Hindsight 长期记忆。

    返回格式化后的记忆文本，如果不可用则返回 None。
    """
    client = _get_client()
    # 如果 Hindsight 客户端不可用，返回 None 表示无法搜索
    if client is None:
        return None

    try:
        resp = client.recall(
            bank_id=bank_id,
            query=query,
            budget=budget,
            max_tokens=max_tokens,
        )
        # 防御：resp 可能为 None 或缺少 results 属性
        results = getattr(resp, "results", None) if resp is not None else None
        if not results:
            return None
        lines = [f"- {r.text}" for r in results if getattr(r, "text", "")]
        return "\n".join(lines) if lines else None
    except Exception as exc:
        logger.warning("Hindsight 召回失败: %s", exc)
        return None


def reflect(
    query: str,
    *,
    bank_id: str = "agentbase",
    budget: str = "mid",
) -> str | None:
    """从 Hindsight 长期记忆中综合生成答案。

    返回综合后的文本，如果不可用则返回 None。
    """
    client = _get_client()
    # 如果 Hindsight 客户端不可用，返回 None
    if client is None:
        return None

    try:
        resp = client.reflect(bank_id=bank_id, query=query, budget=budget)
        return resp.text or None
    except Exception as exc:
        logger.warning("Hindsight 综合失败: %s", exc)
        return None


def _bank_id(workspace_id: int | None) -> str:
    """构造按工作区隔离的 bank_id。"""
    if workspace_id:
        return f"agentbase-workspace-{workspace_id}"
    return "agentbase-default"


def retain_conversation(
    query: str,
    response: str,
    *,
    library_name: str = "",
    customer_name: str = "",
    workspace_id: int | None = None,
    bank_id: str = "agentbase-default",
) -> bool:
    """将完整的对话轮次推送到 Hindsight 记忆。

    格式化问答对并用资料库/客户上下文进行标注。
    """
    content_parts = [f"Q: {query}", f"A: {response}"]
    context = "agentbase conversation"
    if workspace_id:
        context += f" — workspace: {workspace_id}"
    if library_name:
        context += f" — library: {library_name}"
    if customer_name:
        context += f" — customer: {customer_name}"
    content = "\n".join(content_parts)
    bid = _bank_id(workspace_id) if workspace_id else bank_id
    return retain(content, context=context, bank_id=bid)


# 每个工作区一份独立记忆；**不再写** Hermes 的全局 MEMORY.md ——
# Hermes 会把全局文件注入每个 agent 的 system prompt，多工作区下会互相泄漏。
_MEMORY_MAX_CHARS = 200_000      # 单文件上限（超出丢弃最旧条目）
_MEMORY_INJECT_CHARS = 4_000     # 注入 prompt 的字符上限


def workspace_memory_path(workspace_id: int, workspace_slug: str | None = None) -> Path:
    """返回工作区独立记忆文件路径。"""
    from agentbase.paths import hermes_home

    key = (workspace_slug or f"ws-{workspace_id}").strip() or f"ws-{workspace_id}"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in key)[:80]
    return hermes_home() / "memories" / "workspaces" / f"{safe}.md"


def read_workspace_memory(
    workspace_id: int,
    workspace_slug: str | None = None,
    *,
    max_chars: int = _MEMORY_INJECT_CHARS,
) -> str:
    """读取本工作区记忆（最新在前），按上限截断后返回。"""
    path = workspace_memory_path(workspace_id, workspace_slug)
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not content:
        return ""
    if len(content) > max_chars:
        content = content[:max_chars].rstrip() + "\n…（更早的记忆已省略）"
    return content


def _append_workspace_memory(path: Path, entry: str) -> bool:
    """带跨进程锁地追加记忆；锁文件保留、不 unlink（避免 inode 竞争）。"""
    import time as _time

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + ".lock")
        if lock_path.is_symlink():
            return False
        lock_fd = open(str(lock_path), "a+")
    except OSError:
        return False

    try:
        for _attempt in range(5):
            try:
                if os.name == "nt":
                    import msvcrt as _msvcrt
                    lock_fd.seek(0)
                    _msvcrt.locking(lock_fd.fileno(), _msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl as _fcntl
                    _fcntl.flock(lock_fd.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                _time.sleep(0.05)
        else:
            return False

        try:
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            content = entry + ("\n" + existing if existing else "")
            if len(content) > _MEMORY_MAX_CHARS:
                cut = content.rfind("\n", 0, _MEMORY_MAX_CHARS)
                content = content[: max(cut, 0)]
            path.write_text(content, encoding="utf-8")
            return True
        finally:
            if os.name == "nt":
                import msvcrt as _msvcrt
                lock_fd.seek(0)
                _msvcrt.locking(lock_fd.fileno(), _msvcrt.LK_UNLCK, 1)
            else:
                import fcntl as _fcntl
                _fcntl.flock(lock_fd.fileno(), _fcntl.LOCK_UN)
    finally:
        lock_fd.close()


def retain_to_hermes_memory(
    query: str,
    response: str,
    *,
    workspace_id: int | None = None,
    workspace_slug: str | None = None,
    workspace_name: str = "",
    library_name: str = "",
    customer_name: str = "",
    limit: int = 200,
) -> bool:
    """把对话摘要追加到**本工作区**的独立记忆文件。

    历史实现写 $HERMES_HOME/memories/MEMORY.md；Hermes 会把该文件整份注入
    每个 agent 的 system prompt，多工作区下会互相泄漏。现在按工作区分文件，
    由 agentbase.helpers.build_query 只注入当前工作区的内容。
    """
    if workspace_id is None or int(workspace_id) <= 0:
        return False
    if not query or not query.strip():
        return False

    import datetime as _dt

    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    q_preview = query.strip()[:limit]
    r_preview = (response or "").strip()[:limit]

    context_parts = []
    if workspace_name:
        from agentbase import business_config

        context_parts.append(business_config.workspace_term() + ": " + workspace_name)
    if library_name:
        context_parts.append("资料库: " + library_name)
    if customer_name:
        context_parts.append("客户: " + customer_name)
    context_str = (" [" + ", ".join(context_parts) + "]") if context_parts else ""

    entry = "\n".join([
        "[" + now + "]" + context_str,
        "  Q: " + q_preview,
        "  A: " + r_preview,
        "",
    ])
    return _append_workspace_memory(
        workspace_memory_path(int(workspace_id), workspace_slug), entry
    )
