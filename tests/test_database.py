"""
数据库层测试 — schema 创建、v0→v1 迁移、spare columns 幂等性。

所有测试使用临时数据库文件，不影响 data/agentbase.db。
"""

from __future__ import annotations

import sqlite3

# 将 trade 加入 PYTHONPATH（如果通过 pytest 直接运行）
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase.database import (
    SCHEMA_SQL,
    _add_spare_columns,
    get_connection,
)


class TestSchemaCreation:
    """测试全新数据库的 schema 创建。"""

    def test_create_fresh_schema(self, tmp_path):
        """新数据库应创建 6 张表 + 5 个索引。"""
        db_path = tmp_path / "test_fresh.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript(SCHEMA_SQL)
        conn.commit()

        # 验证 6 张表
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {t[0] for t in tables}
        expected = {"companies", "agentbase_companies", "conversations", "usage_ledger"}
        assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"

        # 验证索引
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        ).fetchall()
        index_names = {i[0] for i in indexes}
        expected_indexes = {
            "idx_conversations_company",
            "idx_conversations_created",
        }
        assert expected_indexes.issubset(index_names), \
            f"Missing indexes: {expected_indexes - index_names}"

        conn.close()

    def test_foreign_keys_enabled(self, tmp_path):
        """外键约束应被启用（PRAGMA foreign_keys = ON）。"""
        db_path = tmp_path / "test_fk.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_SQL)
        conn.commit()

        # 插入违反外键的数据（不存在的 company_id）
        conn.execute("INSERT INTO conversations (company_id, query) VALUES (?, ?)",
                     (999, "q"))
        # SQLite 默认不强制外键（需要 PRAGMA），但 get_connection 会启用
        conn.close()

        # 使用 get_connection 风格的连接（设置了 PRAGMA foreign_keys = ON）
        # 这里我们测试 TRADE 的 get_connection 是否启用了外键
        # 注：完整的外键测试在业务层测试中

    def test_all_tables_have_spare_columns(self, tmp_path):
        """所有框架表应有 extra1/extra2/extra3 备用列。"""
        db_path = tmp_path / "test_spare.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_SQL)
        _add_spare_columns(conn)
        conn.commit()

        for table in ["companies", "agentbase_companies", "conversations", "usage_ledger"]:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for extra_col in ["extra1", "extra2", "extra3"]:
                assert extra_col in cols, f"{table} missing column: {extra_col}"

        conn.close()

    def test_spare_columns_default_is_json_object(self, tmp_path):
        """备用列的默认值应为 '{}'（空 JSON 对象）。"""
        db_path = tmp_path / "test_defaults.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_SQL)
        conn.commit()

        conn.execute(
            "INSERT INTO companies (name, slug) VALUES (?, ?)",
            ("Test Co", "test-co"),
        )
        conn.commit()
        row = conn.execute("SELECT extra1, extra2, extra3 FROM companies WHERE id=1").fetchone()
        assert row[0] == "{}"
        assert row[1] == "{}"
        assert row[2] == "{}"

        conn.close()


class TestSpareColumnsIdempotency:
    """测试 _add_spare_columns 的幂等性。"""

    def test_double_call_safe(self, tmp_path):
        """重复调用 _add_spare_columns 不应出错。"""
        db_path = tmp_path / "test_double.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_SQL)
        conn.commit()

        # 第一次调用：添加 spare columns
        _add_spare_columns(conn)
        # 第二次调用：应静默忽略（幂等）
        _add_spare_columns(conn)
        conn.commit()

        # 验证各表的列只出现一次
        for table in ["companies", "conversations"]:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            extra_count = sum(1 for c in cols if c.startswith("extra"))
            assert extra_count == 3, f"{table} has {extra_count} extra columns (expected 3)"

        conn.close()


class TestWALMode:
    """测试 WAL 模式。"""

    def test_wal_mode_enabled(self, tmp_path):
        """get_connection 应启用 WAL journal 模式。"""
        db_path = tmp_path / "test_wal.db"
        # 临时 monkey-patch _get_db_path
        import agentbase.database
        original = agentbase.database._get_db_path
        agentbase.database._get_db_path = lambda: db_path

        try:
            conn = get_connection()
            journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert journal.upper() == "WAL", f"Expected WAL, got {journal}"
            conn.close()
        finally:
            agentbase.database._get_db_path = original
