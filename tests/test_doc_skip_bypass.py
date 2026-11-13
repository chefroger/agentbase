"""doc_skip 旁路回归：不再只拦 read_file，按路径扫描所有工具参数。

复现清单（2026-11-13）：
- read_file：对照组，必须拦
- terminal：`cat <path>`，修前拦住失败
- execute_code：`open(<path>).read()`，修前拦住失败
- search_files：`path=<path>` 内容搜索，修前拦住失败
- delegate_task：嵌套任务 goal/context 含路径，修前拦住失败
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase.hermes_chat_memory_plugin import doc_skip  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_skips():
    doc_skip._skips.clear()
    yield
    doc_skip._skips.clear()


@pytest.fixture
def target(tmp_path):
    path = tmp_path / "repro.txt"
    path.write_text("REPRO_MARKER\n", encoding="utf-8")
    doc_skip.register("task-1", [str(path)])
    return path


def _blocked(tool: str, args, task_id: str = "task-1") -> bool:
    result = doc_skip.on_pre_tool_call(tool, args, task_id=task_id)
    return bool(result and result.get("action") == "block")


def test_read_file_still_blocked(target):
    assert _blocked("read_file", {"path": str(target)})


def test_terminal_command_blocked(target):
    assert _blocked("terminal", {"command": f"cat {target}"})


def test_execute_code_blocked(target):
    code = f"print(open({str(target)!r}).read())"
    assert _blocked("execute_code", {"code": code})


def test_search_files_path_blocked(target):
    assert _blocked("search_files", {
        "pattern": "REPRO_MARKER", "target": "content", "path": str(target),
    })


def test_delegate_task_nested_args_blocked(target):
    args = {
        "tasks": [{
            "goal": "读取这个文件并回报第一行",
            "context": f"文件路径：{target}",
        }],
    }
    assert _blocked("delegate_task", args)


def test_unrelated_file_not_blocked(target, tmp_path):
    other = tmp_path / "other.txt"
    other.write_text("OTHER\n", encoding="utf-8")
    assert not _blocked("terminal", {"command": f"cat {other}"})


def test_tool_without_skipped_path_not_blocked(target):
    assert not _blocked("terminal", {"command": "ls -la /tmp"})
    assert not _blocked("terminal", {})
    assert not _blocked("write_file", {"path": "/tmp/unrelated.txt", "content": "x"})


def test_release_stops_blocking(target):
    doc_skip.release("task-1")
    assert not _blocked("terminal", {"command": f"cat {target}"})


def test_fail_open_on_unexpected_args():
    assert doc_skip.on_pre_tool_call("terminal", object(), task_id="task-1") is None
