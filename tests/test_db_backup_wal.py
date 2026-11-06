"""迁移前备份必须走在线快照，不能裸拷 WAL 主库。

主库是 WAL 模式：最近提交的事务可能只存在于 `-wal` 文件里。裸 `copy2` 主库
文件会得到一个缺少最新数据的备份，而迁移一旦失败，回退到的就是这份旧数据。
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_backup_contains_rows_still_in_wal(tmp_path):
    """WAL 未 checkpoint + 写入连接仍占用时，备份必须包含最新已提交行。"""
    from agentbase.database import _backup_db

    db = tmp_path / "data" / "agentbase.db"
    db.parent.mkdir()
    writer = sqlite3.connect(db)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE t (v TEXT)")
        writer.commit()
        writer.execute("INSERT INTO t VALUES ('committed-in-wal')")
        writer.commit()

        wal = db.with_name(db.name + "-wal")
        assert wal.is_file() and wal.stat().st_size > 0, (
            "前提不成立：已提交事务没有留在 WAL 里"
        )

        backup = _backup_db(db)
        assert backup is not None and backup.is_file()
    finally:
        writer.close()

    conn = sqlite3.connect(f"file:{backup}?mode=ro", uri=True)
    try:
        assert conn.execute(
            "SELECT count(*) FROM t WHERE v='committed-in-wal'"
        ).fetchone()[0] == 1, "备份丢了 WAL 里已提交的最新数据"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()
