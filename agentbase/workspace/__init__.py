"""
AgentBase — 公司数据层。

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
    get_trade_workspace,
    list_all,
    purge,
    slug_from_id,
    update,
    update_trade_workspace,
)

# 从 workdir 模块导出工作目录管理的公开函数和常量
from agentbase.workspace.workdir import (
    _WORK_DIR_CATEGORIES,
    _ensure_data_dir,
    _setup_work_directory,
    _slugify,
    _validate_slug,
)

# __all__ 明确列出所有公开 API（IDE 自动补全 / import * 的边界）
__all__ = [
    # 数据目录常量
    "AGENT_HOME",
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
    "get_trade_workspace",
    "update_trade_workspace",
    "get_agent_identity",
    # 工作目录管理
    "_WORK_DIR_CATEGORIES",
    "_setup_work_directory",
    # 工具函数（供内部使用）
    "_slugify",
    "_validate_slug",
    "_ensure_data_dir",
]
