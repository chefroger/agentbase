"""cron 完成判定只认任务自己的产出目录，不按正文子串猜。

Hermes 的产出路径是 ``cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md``。
旧实现扫描所有任务目录、以「任务名出现在正文里」判完成，别的任务输出
提到这个名字就会误判（审计 P2）。
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def cron_env(monkeypatch, tmp_path):
    import agentbase.api.cron as cron

    output = tmp_path / "output"
    output.mkdir()
    jobs = tmp_path / "jobs.json"
    monkeypatch.setattr(cron, "_cron_output", lambda: output)
    monkeypatch.setattr(cron, "_jobs_file", lambda: jobs)
    return cron, output, jobs


def _write_output(output: Path, job_id: str, day: str, text: str) -> None:
    job_dir = output / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / f"{day}_09-00-00.md").write_text(text, encoding="utf-8")


def test_reads_only_that_jobs_directory(cron_env):
    cron, output, _ = cron_env
    today = date.today().isoformat()
    _write_output(output, "job-a", today, "A 输出")
    _write_output(output, "job-b", today, "B 输出，顺便提到 A 的任务")

    assert cron._find_cron_output("A 的任务", today, job_id="job-a") == "A 输出"
    assert cron._find_cron_output("A 的任务", today, job_id="missing") is None


def test_decoy_content_does_not_count(cron_env):
    cron, output, _ = cron_env
    today = date.today().isoformat()
    # 别的任务正文提到 A 的任务、日期也对 —— 不得据此判 A 完成
    _write_output(output, "job-b", today, "B 输出提到 A 的任务")

    assert cron._find_cron_output("A 的任务", today, job_id="job-a") is None
    # 没有 job_id 时不猜（旧正文子串匹配已移除）
    assert cron._find_cron_output("A 的任务", today) is None


def test_wrong_date_returns_none(cron_env):
    cron, output, _ = cron_env
    _write_output(output, "job-a", "2020-01-01", "A 输出")

    assert cron._find_cron_output("A 的任务", date.today().isoformat(), job_id="job-a") is None


def test_today_endpoint_does_not_use_other_jobs_output(cron_env):
    cron, output, jobs = cron_env
    today = date.today().isoformat()
    jobs.write_text(json.dumps({"jobs": [
        {"id": "job-a", "name": "A 的任务", "schedule": {"display": "0 9 * * *"}},
        {"id": "job-b", "name": "B 的任务", "schedule": {"display": "0 10 * * *"}},
    ]}), encoding="utf-8")
    _write_output(output, "job-b", today, "B 输出提到 A 的任务")

    completed = {x["name"] for x in cron.get_today_cron(1)["completed"]}
    assert "A 的任务" not in completed, "别家任务的输出把 A 误判成已完成"
    assert "B 的任务" in completed

    # A 自己的产出出现后才算完成
    _write_output(output, "job-a", today, "A 输出")
    completed = {x["name"] for x in cron.get_today_cron(1)["completed"]}
    assert completed == {"A 的任务", "B 的任务"}
