"""
AgentBase — 工作区数据层。

「工作区」是底座的数据隔离单元；它在用户界面里叫什么（公司/项目/客户/门店）
由 business.yaml 的 workspaces.term 决定，代码层不写死业务称呼。

三模块结构：
  - crud: workspaces + agentbase_workspaces 表的增删改查 + 审计日志
  - workdir: 桌面工作目录管理 + .agentbase-template 模板复制

从 agentbase.workspace import xxx 的方式保持不变，所有公开 API 通过本 __init__ 重导出。
"""

# 从 crud 模块导出所有公开的数据库操作函数
from agentbase.workspace.crud import (
    AGENT_HOME,
    _db_get_one,
    _row_to_tc,
    _row_to_workspace,
    _write_audit_log,
    create,
    delete,
    get,
    get_agent_identity,
    get_by_slug,
    get_workspace_record,
    list_all,
    purge,
    slug_from_id,
    update,
    update_workspace_record,
)

# 从 workdir 模块导出工作目录管理的公开函数和常量
from agentbase.workspace.workdir import (
    _WORK_DIR_CATEGORIES,
    _ensure_data_dir,
    _setup_work_directory,
    _slugify,
    _validate_slug,
)


def ensure_default_workspace() -> dict | None:
    """按 business.yaml 的 workspace 语义决定是否自动创建默认工作区。

    - `workspaces.mode=single` 且 `create_default=true` 才创建
    - `mode=multi` 或 `create_default=false` → 不创建，交给使用方管理
    - 已有活跃工作区 → 什么都不做（幂等）
    - 创建失败（如桌面不可写）→ 返回 None，不阻断服务启动
    """
    from agentbase import business_config
    from agentbase.database import get_connection

    # workspace 语义由 business.yaml 决定（Muse 纠偏：底座不假设单业务）：
    # 只有 single + create_default 才自动创建；multi 交给使用方自行管理。
    semantic = business_config.workspaces_config()
    if semantic.get("mode") != "single" or not semantic.get("create_default", True):
        return None

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM workspaces WHERE is_active = 1"
        ).fetchone()
        if row and row[0] > 0:
            return None
    finally:
        conn.close()

    name = str(business_config.get("business_name") or "").strip() or "AgentBase"
    try:
        return create(name=name)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("自动创建默认工作区失败：%s", exc, exc_info=True)
        return None


# __all__ 明确列出所有公开 API（IDE 自动补全 / import * 的边界）
__all__ = [
    # 数据目录常量
    "AGENT_HOME",
    "ensure_default_workspace",
    # workspaces 表 CRUD
    "create",
    "get",
    "get_by_slug",
    "slug_from_id",
    "list_all",
    "update",
    "delete",
    "purge",
    # agentbase_workspaces 表 CRUD
    "get_workspace_record",
    "update_workspace_record",
    "get_agent_identity",
    # 工作目录管理
    "_WORK_DIR_CATEGORIES",
    "_setup_work_directory",
    # 工具函数（供内部使用）
    "_slugify",
    "_validate_slug",
    "_ensure_data_dir",
]
