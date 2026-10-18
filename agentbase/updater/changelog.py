"""人话更新说明（CHANGELOG.md）。

数据源是仓库根的 `CHANGELOG.md`（打包时作为 datas 进 bundle），
不依赖 GitHub API —— 可离线、可审计。

格式约定：每个版本一个 `## [x.y.z] - YYYY-MM-DD` 段落，条目一行一句。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HEADER_RE = re.compile(r"^##\s+\[([^\]]+)\]\s*(?:-\s*(\S+))?\s*$")
FALLBACK = "修复与稳定性改进"


def changelog_path() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / "CHANGELOG.md"
        return candidate if candidate.is_file() else None
    candidate = Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md"
    return candidate if candidate.is_file() else None


def parse(text: str) -> list[dict]:
    """解析为 [{version, date, lines}]，保持文件顺序（新版本在前）。"""
    entries: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        m = _HEADER_RE.match(raw.strip())
        if m:
            current = {"version": m.group(1).strip(), "date": m.group(2) or "", "lines": []}
            entries.append(current)
            continue
        if current is None:
            continue
        line = raw.strip()
        if line.startswith(("- ", "* ")):
            current["lines"].append(line[2:].strip())
    return entries


def _version_key(value: str):
    try:
        from packaging.version import Version

        return Version(value.lstrip("v"))
    except Exception:
        return None


def entries_between(current: str, latest: str, *, limit: int = 20) -> list[dict]:
    """返回 (current, latest] 区间内的条目，新版本在前。"""
    path = changelog_path()
    if path is None or not latest:
        return []
    try:
        entries = parse(path.read_text(encoding="utf-8"))
    except OSError:
        return []

    cur_key = _version_key(current) if current else None
    latest_key = _version_key(latest)
    if latest_key is None:
        return []

    selected: list[dict] = []
    for entry in entries:
        key = _version_key(entry["version"])
        if key is None or key > latest_key:
            continue
        if cur_key is not None and key <= cur_key:
            continue
        selected.append(entry)
    return selected[:limit]


def render(current: str, latest: str) -> str:
    """给用户看的说明；没有条目时返回兜底文案。"""
    entries = entries_between(current, latest)
    if not entries:
        return FALLBACK
    lines: list[str] = []
    for entry in entries:
        header = f"v{entry['version']}"
        if entry.get("date"):
            header += f"（{entry['date']}）"
        lines.append(header)
        lines.extend(f"· {item}" for item in entry["lines"][:8])
    return "\n".join(lines)
