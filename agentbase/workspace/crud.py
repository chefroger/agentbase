"""
AgentBase — 工作区数据层 CRUD。

管理两张表：
  - workspaces: 工作区基本信息（名称、slug、联系方式、激活状态）
  - agentbase_workspaces: AgentBase 业务扩展信息（数据目录、Agent 身份、会话状态）
"""

from __future__ import annotations

import json as _json
import os
import shutil
from datetime import datetime as _dt
from pathlib import Path

from agentbase.database import get_connection

# ── 模块级常量 ────────────────────────────────────────────────────────────────

# AgentBase 用户数据目录
# 优先级: AGENT_HOME 环境变量 > Windows %LOCALAPPDATA% > ~/.agentbase/
_AGENT_HOME_RAW = os.environ.get("AGENT_HOME", "").strip()
if _AGENT_HOME_RAW:
    AGENT_HOME = Path(_AGENT_HOME_RAW)  # 显式设置，直接使用
elif os.name == "nt":
    _local_appdata = os.environ.get(
        "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
    )
    AGENT_HOME = Path(_local_appdata) / "agentbase"
else:
    AGENT_HOME = Path.home() / ".agentbase"  # macOS / Linux 默认路径


# ── 数据库辅助函数 ────────────────────────────────────────────────────────────

def _db_get_one(sql: str, args: tuple = ()) -> tuple | None:
    """执行单行查询并返回结果行（sqlite3.Row），未找到时返回 None。

    每次调用都从连接池获取新连接，用完即关闭，避免长连接泄漏。
    """
    conn = get_connection()
    try:
        row = conn.execute(sql, args).fetchone()
        return row
    finally:
        conn.close()


def _custom_fields_from_extra(extra1) -> dict:
    try:
        data = _json.loads(extra1 or "{}")
    except (TypeError, ValueError):
        return {}
    fields = data.get("custom_fields") if isinstance(data, dict) else None
    return dict(fields) if isinstance(fields, dict) else {}


def _row_to_workspace(row) -> dict:
    """将 workspaces 表的数据库行转换为业务字典。

    所有字段一一映射，is_active 转为 Python bool 类型；
    extra1 里的自定义字段以 custom_fields 返回。
    """
    keys = row.keys()
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "logo_url": row["logo_url"],
        "website": row["website"],
        "contact_name": row["contact_name"],
        "contact_email": row["contact_email"],
        "address": row["address"],
        "is_active": bool(row["is_active"]),
        "custom_fields": _custom_fields_from_extra(row["extra1"]) if "extra1" in keys else {},
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_tc(row) -> dict:
    """将 agentbase_workspaces 表的数据库行转换为业务字典。

    is_active 转为 Python bool，其余字段原样返回。
    """
    return {
        "workspace_id": row["workspace_id"],
        "data_dir": row["data_dir"],
        "agent_identity_md": row["agent_identity_md"],
        "is_active": bool(row["is_active"]),
        "extra1": row["extra1"] if "extra1" in row.keys() else None,
        "created_at": row["created_at"],
    }


# ── workspaces 表 CRUD ─────────────────────────────────────────────────────────

def list_all(include_inactive: bool = False) -> list[dict]:
    """返回未软删除的工作区列表（脱敏版），按名称排序。

    脱敏：仅返回 id/name/slug/is_active，不暴露 contact_email/address 等 PII。
    详情通过 get() 获取完整字段。

    Args:
        include_inactive: True 时包含 is_active=0 的软删除工作区
    """
    conn = get_connection()
    try:
        if include_inactive:
            # 包含所有工作区（管理员视图）
            sql = "SELECT id, name, slug, is_active, extra1 FROM workspaces ORDER BY name"
            rows = conn.execute(sql).fetchall()
        else:
            # 默认仅返回活跃工作区（用户视图），软删除的工作区不出现
            sql = (
                "SELECT id, name, slug, is_active, extra1 FROM workspaces "
                "WHERE is_active = 1 ORDER BY name"
            )
            rows = conn.execute(sql).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "slug": r["slug"],
                "is_active": bool(r["is_active"]),
                "custom_fields": _custom_fields_from_extra(r["extra1"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get(workspace_id: int, *, include_inactive: bool = False) -> dict | None:
    """返回工作区完整字典（含所有字段），未找到时返回 None。

    默认排除软删除（is_active=0）的行；purge 等维护流程显式传
    ``include_inactive=True``。
    """
    sql = "SELECT * FROM workspaces WHERE id = ?"
    if not include_inactive:
        sql += " AND is_active = 1"
    row = _db_get_one(sql, (workspace_id,))
    return _row_to_workspace(row) if row else None


def slug_from_id(workspace_id: int) -> str | None:
    """根据工作区 ID 返回 slug（仅活跃工作区）。"""
    row = _db_get_one(
        "SELECT slug FROM workspaces WHERE id = ? AND is_active = 1", (workspace_id,)
    )
    return row[0] if row else None


def get_by_slug(slug: str) -> dict | None:
    """根据 slug 返回工作区字典，未找到时返回 None。

    用于通过 URL 中的 slug 标识查找工作区。
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, slug, logo_url, website, contact_name, "
            "contact_email, address, is_active, created_at, updated_at "
            "FROM workspaces WHERE slug = ? AND is_active = 1",
            (slug,),
        ).fetchone()
        return _row_to_workspace(row) if row else None
    finally:
        conn.close()


def create(
    name: str,
    slug: str | None = None,
    logo_url: str = "",
    website: str = "",
    contact_name: str = "",
    contact_email: str = "",
    address: str = "",
    *,
    work_dir_name: str = "",
    custom_fields: dict | None = None,
) -> dict:
    """创建新工作区，同时创建 agentbase_workspaces 记录 + 桌面工作目录 + 文档库。

    事务保护：任何步骤失败都会回滚数据库并清理已创建的目录。

    Args:
        name: 工作区名称（必填）
        slug: URL 标识（省略时从 name 自动生成）
        work_dir_name: 桌面工作目录的自定义名称（为空则用工作区名）

    Returns:
        完整工作区字典 + work_dir / work_dir_is_new / libraries 扩展字段
    """
    from agentbase.workspace.workdir import (
        _ensure_data_dir,
        _setup_work_directory,
        _slugify,
        _validate_slug,
    )

    if not name or not name.strip():
        raise ValueError("Workspace name cannot be empty")

    if not slug:
        # 中文（或纯非 ASCII）名称经 _slugify 后为空 —— 用 "workspace" 兜底，
        # 与前端 autoSlug 的行为一致；否则默认 business_name（如「示例业务」）
        # 会让首启自动创建工作区直接失败。
        slug = _slugify(name) or "workspace"
    slug = _validate_slug(slug)  # 校验 slug 合法性（防路径穿越、非法字符）

    data_dir = None
    data_dir_is_new = False  # 只有本次新建的数据目录才允许在失败补偿时删除
    work_dir = None
    workspace_id = None  # 哨兵：失败补偿时据此判断「本次是否真的插入过工作区」
    is_new = True  # 标记工作目录是否为新创建（回滚时据此决定是否清理）
    conn = get_connection()

    try:
        # 串行化同名 slug 的“先查后插”：并发创建不能共用同一个数据目录。
        conn.execute("BEGIN IMMEDIATE")

        # slug 唯一性检查：冲突时自动追加 -N 后缀
        base_slug = slug
        counter = 1
        while True:
            existing = conn.execute(
                "SELECT id FROM workspaces WHERE slug = ?", (slug,)
            ).fetchone()
            if not existing:
                break
            counter += 1
            slug = f"{base_slug}-{counter}"

        # 1) 创建 ~/.agentbase/{slug}/ 数据目录
        #    先记录“是否本来就不存在”，失败补偿只删除本次新建的目录。
        data_dir_is_new = not (AGENT_HOME / slug).exists()
        data_dir = str(_ensure_data_dir(slug, AGENT_HOME))

        # 2) 创建桌面工作目录（分类来自 business.yaml）
        work_dir, is_new = _setup_work_directory(
            name, slug, suggested_name=work_dir_name
        )

        # 3) 写入 workspaces 表（自定义字段存 extra1）
        _custom = custom_fields if isinstance(custom_fields, dict) else {}
        _extra_ws = _json.dumps({"custom_fields": _custom}, ensure_ascii=False)
        cursor = conn.execute(
            "INSERT INTO workspaces (name, slug, logo_url, website, "
            "contact_name, contact_email, address, extra1) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, slug, logo_url, website, contact_name, contact_email, address, _extra_ws),
        )
        workspace_id = cursor.lastrowid

        # 4) 写入 agentbase_workspaces 表（工作目录路径存入 extra1 JSON）
        _extra1 = _json.dumps({"work_dir": str(work_dir)})
        conn.execute(
            "INSERT INTO agentbase_workspaces (workspace_id, data_dir, extra1) "
            "VALUES (?, ?, ?)",
            (workspace_id, data_dir, _extra1),
        )
        conn.commit()

        result = get(workspace_id)
        if result:
            result["work_dir"] = str(work_dir)
            result["work_dir_is_new"] = is_new
        return result

    except Exception:
        conn.rollback()  # 回滚尚未提交的部分
        # 补偿删除：工作区在「注册文档库」之前就已经 commit（不能把 commit 后移 ——
        # library.create 走独立连接，而 PRAGMA foreign_keys=ON，未提交的工作区行对它
        # 不可见，会触发外键失败），所以 rollback 覆盖不到这一段，必须显式删掉，
        # 否则用户重试会立刻撞 `UNIQUE constraint failed: workspaces.slug`。
        if workspace_id is not None:
            # 逐条兜住：业务表（如旧 libraries）可能已随剥离删除，
            # 第一条失败不能挡住后面真正需要的补偿删除。
            for _sql in (
                "DELETE FROM libraries WHERE workspace_id = ?",
                "DELETE FROM agentbase_workspaces WHERE workspace_id = ?",
                "DELETE FROM workspaces WHERE id = ?",
            ):
                try:
                    conn.execute(_sql, (workspace_id,))
                except Exception:
                    pass
            try:
                conn.commit()
            except Exception:
                pass  # 补偿失败不掩盖原始异常
        # 清理本事务中创建的文件系统资源（仅清理本次新建的目录）
        import shutil as _shutil

        if is_new and work_dir and work_dir.exists():
            try:
                _shutil.rmtree(str(work_dir))
            except OSError:
                pass  # 目录清理失败不影响原始异常抛出
        if data_dir and data_dir_is_new:
            _data_path = Path(data_dir)
            if _data_path.exists():
                try:
                    _shutil.rmtree(str(_data_path))
                except OSError:
                    pass
        raise  # 重新抛出原始异常
    finally:
        conn.close()


def update(
    workspace_id: int,
    name: str | None = None,
    logo_url: str | None = None,
    website: str | None = None,
    contact_name: str | None = None,
    contact_email: str | None = None,
    address: str | None = None,
    is_active: bool | None = None,
    custom_fields: dict | None = None,
) -> dict | None:
    """更新工作区字段。仅更新传入的非 None 字段（部分更新）。

    `custom_fields` 传入时整体替换 workspaces.extra1 里的自定义字段。
    返回更新后的工作区字典，工作区不存在时返回 None。
    """
    conn = get_connection()
    try:
        if not conn.execute(
            "SELECT 1 FROM workspaces WHERE id = ?", (workspace_id,)
        ).fetchone():
            return None  # 工作区不存在

        # 动态构建 SET 子句，只更新传入的非 None 字段
        fields, vals = [], []
        for fname, fval in [
            ("name", name),
            ("logo_url", logo_url),
            ("website", website),
            ("contact_name", contact_name),
            ("contact_email", contact_email),
            ("address", address),
        ]:
            if fval is not None:
                fields.append(f"{fname} = ?")
                vals.append(fval)

        if is_active is not None:
            fields.append("is_active = ?")
            vals.append(1 if is_active else 0)

        if custom_fields is not None:
            row = conn.execute(
                "SELECT extra1 FROM workspaces WHERE id = ?", (workspace_id,)
            ).fetchone()
            try:
                extra = _json.loads(row["extra1"] or "{}") if row else {}
            except (TypeError, ValueError):
                extra = {}
            if not isinstance(extra, dict):
                extra = {}
            extra["custom_fields"] = dict(custom_fields)
            fields.append("extra1 = ?")
            vals.append(_json.dumps(extra, ensure_ascii=False))

        if fields:
            # 仅当有字段需要更新时才执行 SQL
            fields.append("updated_at = datetime('now', 'localtime')")
            vals.append(workspace_id)
            conn.execute(
                f"UPDATE workspaces SET {', '.join(fields)} WHERE id = ?", vals
            )
            conn.commit()

        return get(workspace_id)
    finally:
        conn.close()


def delete(workspace_id: int) -> bool:
    """软删除工作区：设置 is_active=0 + 记录 deleted_at 时间戳。

    数据保留 30 天后由 purge() 执行物理清理。
    返回 True 表示软删除成功，False 表示工作区不存在或已删除。
    """
    conn = get_connection()
    try:
        n = conn.execute(
            "UPDATE workspaces SET is_active = 0, "
            "updated_at = datetime('now','localtime') "
            "WHERE id = ? AND is_active = 1",
            (workspace_id,),
        ).rowcount
        if n > 0:
            # 鉴权查的是 agentbase_workspaces.is_active —— 必须同步停用，
            # 否则“已删除”的工作区仍能通过 require_workspace。
            conn.execute(
                "UPDATE agentbase_workspaces SET is_active = 0 WHERE workspace_id = ?",
                (workspace_id,),
            )
        conn.commit()
        if n > 0:
            # 写入审计日志（用于后续 30 天倒计时清理）
            _write_audit_log(workspace_id, "soft_delete", "工作区已软删除，数据保留 30 天")
        return n > 0
    finally:
        conn.close()


def purge(workspace_id: int) -> bool:
    """物理删除工作区及其所有关联数据 + 清理文件系统数据目录。

    仅管理员调用。不可逆操作。执行前先写入审计日志。
    返回 True 表示删除成功。
    """
    tc = get_workspace_record(workspace_id)
    workspace = get(workspace_id, include_inactive=True)
    slug = workspace["slug"] if workspace else None
    data_dir_str = tc["data_dir"] if tc else None

    # 提取桌面工作目录路径（存于 extra1 JSON）
    work_dir_str = ""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT extra1 FROM agentbase_workspaces WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if row and row["extra1"]:
            try:
                work_dir_str = _json.loads(row["extra1"]).get("work_dir", "") or ""
            except (ValueError, TypeError):
                work_dir_str = ""
    finally:
        conn.close()

    # 写入审计日志（不可逆操作前的最终记录）
    _write_audit_log(workspace_id, "purge", "物理删除工作区及所有数据")

    conn = get_connection()
    try:
        n = conn.execute(
            "DELETE FROM workspaces WHERE id = ?", (workspace_id,)
        ).rowcount
        conn.commit()
        if n > 0:
            # 清理文件系统：agentbase_workspaces.data_dir（仅当目录在 AGENT_HOME 下）
            if data_dir_str:
                data_path = Path(data_dir_str)
                if data_path.exists():
                    try:
                        # 安全校验：确保 data_dir 在 AGENT_HOME 下，防止误删系统目录
                        data_path.resolve().relative_to(AGENT_HOME.resolve())
                    except ValueError:
                        pass  # 不在 AGENT_HOME 下，跳过清理（不删除外部目录）
                    else:
                        try:
                            shutil.rmtree(data_path)
                        except OSError:
                            pass  # 目录清理失败不抛异常
            # 清理文件系统：~/.agentbase/{slug}/
            if slug:
                slug_dir = AGENT_HOME / slug
                if slug_dir.exists():
                    try:
                        shutil.rmtree(slug_dir)
                    except OSError:
                        pass
            # 清理桌面工作目录（仅当位于桌面目录下，防止误删用户数据）
            if work_dir_str:
                work_path = Path(work_dir_str)
                if work_path.exists():
                    try:
                        from agentbase.workspace.workdir import _get_desktop_path
                        desktop = _get_desktop_path().resolve()
                        work_path.resolve().relative_to(desktop)
                    except ValueError:
                        pass  # 不在桌面下，跳过清理
                    else:
                        try:
                            shutil.rmtree(work_path)
                        except OSError:
                            pass
        return n > 0
    finally:
        conn.close()


# ── agentbase_workspaces 表 CRUD ────────────────────────────────────────────────────

def get_workspace_record(workspace_id: int) -> dict | None:
    """返回工作区对应的 agentbase_workspaces 记录，未找到时返回 None。

    agentbase_workspaces 表存储 AgentBase 业务扩展数据：data_dir、agent_identity_md 等。
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT workspace_id, data_dir, agent_identity_md, is_active, extra1, created_at "
            "FROM agentbase_workspaces WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        return _row_to_tc(row) if row else None
    finally:
        conn.close()


def update_workspace_record(
    workspace_id: int,
    data_dir: str | None = None,
    agent_identity_md: str | None = None,
    is_active: bool | None = None,
    extra1: str | None = None,
) -> dict | None:
    """更新 agentbase_workspaces 字段（部分更新）。

    仅更新传入的非 None 字段。extra1 字段存储 JSON（工作目录路径等元数据）。
    """
    conn = get_connection()
    try:
        if not conn.execute(
            "SELECT 1 FROM agentbase_workspaces WHERE workspace_id = ?", (workspace_id,)
        ).fetchone():
            return None  # agentbase_workspaces 记录不存在

        fields, vals = [], []
        if data_dir is not None:
            fields.append("data_dir = ?")
            vals.append(data_dir)
        if agent_identity_md is not None:
            fields.append("agent_identity_md = ?")
            vals.append(agent_identity_md)
        if is_active is not None:
            fields.append("is_active = ?")
            vals.append(1 if is_active else 0)
        if extra1 is not None:
            fields.append("extra1 = ?")
            vals.append(extra1)

        if fields:
            vals.append(workspace_id)
            conn.execute(
                f"UPDATE agentbase_workspaces SET {', '.join(fields)} "
                "WHERE workspace_id = ?",
                vals,
            )
            conn.commit()

        return get_workspace_record(workspace_id)
    finally:
        conn.close()


def get_agent_identity(workspace_id: int) -> str:
    """返回工作区的 Agent 身份文本（与最终提示词口径一致：**磁盘文件优先**）。

    优先级链（高到低）：
      1. {data_dir}/workspaces/{slug}/agent-identity.md（用户手动编辑 / 身份写接口）
      2. agentbase_workspaces.agent_identity_md 数据库字段（运行时缓存）
      3. '' → 回退到通用 AGENTBASE_SYSTEM_PROMPT

    注意：磁盘路径必须与工作目录/模板布局（_ensure_data_dir → {data_dir}/workspaces/{slug}/）
    及 agentbase.prompts._workspace_identity_path 保持一致，否则文件永远命中不了。
    """
    tc = get_workspace_record(workspace_id)
    if not tc:
        return ""

    # 1) 磁盘文件优先（与 prompts._resolve_custom_prompt 一致）
    data_dir = Path(tc["data_dir"]) if tc.get("data_dir") else None
    slug = slug_from_id(workspace_id)
    if data_dir and slug:
        identity_file = data_dir / "workspaces" / slug / "agent-identity.md"
        if identity_file.is_file():
            try:
                content = identity_file.read_text(encoding="utf-8").strip()
            except OSError:
                content = ""
            if content:
                return content

    # 2) 数据库缓存
    if tc.get("agent_identity_md"):
        return tc["agent_identity_md"]

    return ""


# ── 审计日志 ──────────────────────────────────────────────────────────────────

def _audit_dir() -> Path:
    """审计日志目录: ~/.agentbase/audit/。

    按天分文件: YYYY-MM-DD.jsonl，每行一条 JSON 记录。
    """
    d = AGENT_HOME / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_audit_log(workspace_id: int, action: str, detail: str) -> None:
    """追加一行 JSON 审计日志到当天的审计文件中。

    审计日志记录所有敏感操作（创建、软删除、物理删除），用于追溯。

    Args:
        workspace_id: 操作的数据库工作区 ID
        action: 操作类型（如 "soft_delete"、"purge"）
        detail: 操作详情的自然语言描述
    """
    log_file = _audit_dir() / f"{_dt.now().strftime('%Y-%m-%d')}.jsonl"
    entry = _json.dumps(
        {
            "ts": _dt.now().isoformat(),
            "workspace_id": workspace_id,
            "action": action,
            "detail": detail,
        },
        ensure_ascii=False,
    )
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        import logging
        logging.warning("审计日志写入失败: %s", log_file)
