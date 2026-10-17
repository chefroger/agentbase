"""
AgentBase AI Assistant — Post-install 工具包。

四模块结构：
  - skills: skill 安装/更新 + 模板复制
  - update: 一键系统更新 (agentbase-update)
  - backup: 系统数据备份/还原 (agentbase-backup / agentbase-restore)
  - __init__: CLI 入口 + 重导出

从 agentbase.post_install import xxx 保持向后兼容。
"""

from agentbase.post_install.backup import backup_agentbase, restore_agentbase
from agentbase.post_install.skills import install_skills, update_skills
from agentbase.post_install.update import update_agentbase

__all__ = [
    "install_skills",
    "update_skills",
    "update_agentbase",
    "backup_agentbase",
    "restore_agentbase",
]


# ── CLI 入口 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AgentBase Skills Manager")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("install", help="Install skills from local package")
    sub.add_parser("update", help="Update skills from GitHub")
    p_up = sub.add_parser("update-agentbase", help="Update entire AgentBase system")
    p_backup = sub.add_parser("backup", help="Backup AgentBase data")
    p_backup.add_argument(
        "--output", "-o", default=None, help="Output directory (default: Desktop)"
    )

    args = parser.parse_args()
    if args.command == "update":
        update_skills()  # 从 GitHub 更新 skills
    elif args.command == "update-agentbase":
        update_agentbase()  # 一键更新整个 AgentBase 系统
    elif args.command == "backup":
        backup_agentbase(args.output)  # 备份 AgentBase 数据到 tar.gz
    else:
        install_skills()  # 默认：从本地包安装 skills
