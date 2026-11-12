"""文档提取缓存手工基准脚本 —— agentbase 版（路线 A：走完整聊天）。

跑法（用 trade 的 venv，PYTHONPATH 指向本仓根目录即可，无需安装）：

    AGENT_HOME=/tmp/agentbase-bench-run \
    PYTHONPATH=/Users/rogerlau/Desktop/agentbase-workspace/agentbase \
    ~/.trade/venv/bin/python scripts/benchmark-doc-cache.py \
        --rounds 2 --home /tmp/agentbase-bench-run --out /tmp/bench-agentbase.json

与 trade 版**同一文档集、同一问题集**，但有一处产品差异必须写进报告：

- trade 用 `library_id` 挂文档库；**agentbase 没有文档库实体**，文档计划靠问句里
  点名路径（`agentbase/api/chat.py:_build_document_plan` → `helpers._extract_named_paths`）。
  因此 agentbase 每道题都在题面末尾带一个**中性固定**目录 `/tmp/agentbase-bench-docs`
  —— 路径里若带数字或「客户/报价」等词，`doc_scope` 会把 scope 判成 full_read，
  缓存旁路根本不会触发。
- 题面因此比 trade 版多一个路径后缀，其余一致。

记录口径、Hermes 侧临时改动、缓存判定规则与 trade 版完全相同。
脚本只做基准，不进产品逻辑。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# ── 文档集（真实业务文档，不进仓库；只记文件名/分类/哈希）──────────────

DOC_SOURCE_ROOT = Path.home() / "Desktop" / "外贸业务资料包" / "外贸业务资料包"

# agentbase 没有文档库实体：文档计划靠问句里点名路径。目录名必须中性且固定，
# 路径里带数字或「客户/报价」等词会把 scope 判成 full_read。
BENCH_DOCS_DIR = "/tmp/agentbase-bench-docs"

DOCUMENTS = [
    {
        "key": "quotation",
        "name": "产品报价单（外贸协议订单版本，含打版等复杂信息）1.xlsx",
        "rel": "01-外贸报价模板/产品报价单（外贸协议订单版本，含打版等复杂信息）1.xlsx",
        "role": "money 典型（金额结构）；改数验证对象",
        "expect_kind": "money",
        "parse": "ok",
    },
    {
        "key": "ces_table",
        "name": "万腾CES展产品表(最终确定版本-2018.12.22）.xlsx",
        "rel": "06-更多销售技巧，模板拿下客户/有效沟通细节图工具/"
               "万腾CES展产品表(最终确定版本-2018.12.22）.xlsx",
        "role": "产品表：11-09 被金额兜底误判 money 的那类，分类观察点",
        "expect_kind": "info",
        "parse": "ok",
    },
    {
        "key": "crm_big",
        "name": "客户跟进管理系统-外贸.xlsx",
        "rel": "03-客户盘点管理表/客户跟进管理系统-外贸.xlsx",
        "role": "Excel 超大表（2.5MB）：截断口径观察点",
        "expect_kind": None,
        "parse": "truncated",
    },
    {
        "key": "perf_stats",
        "name": "个人业绩统计表.xlsx",
        "rel": "07-外贸业务工作管理表格/个人业绩统计表.xlsx",
        "role": "Excel 统计表：数字题主力",
        "expect_kind": None,
        "parse": "ok",
    },
    {
        "key": "cold_email_docx",
        "name": "高效开发信的全方位建议.docx",
        "rel": "02-客户开发与订单管理/高效开发信的全方位建议.docx",
        "role": "Word prose（无表格）：Word 抽取观察点",
        "expect_kind": "info",
        "parse": "ok",
    },
    {
        "key": "negotiation_docx",
        "name": "业务转化提升分享第二篇.docx",
        "rel": "06-更多销售技巧，模板拿下客户/业务转化提升分享第二篇.docx",
        "role": "Word 含数值（7000USD）：Word 数字题",
        "expect_kind": None,
        "parse": "ok",
    },
]

# 报价单里用于改数验证的字面数值（M6 = 报价单号 2018123），改后核对答案。
QUOTATION_ORIGINAL_TOTAL = 2018123
QUOTATION_MUTATED_TOTAL = 2018999

# ── 问题集（全文进报告）─────────────────────────────────────────────────
#
# 提问一律对**整个文档库**（6 个文件），这是产品设计的用法：缓存只服务
# 概览/定位两类请求，针对单个文件的具体事实按规则一律全文读
# （`agentbase/doc_scope.py`）。每道题的 scope 由 `detect_request_scope` 判定，
# 脚本会实测并写进结果，不靠这里的标注。
#
# summary/locate 题刻意避开 doc_scope 的 full_read 触发词（数字、价格、
# 金额、客户、统计、比较……），否则会被判成 full_read、缓存根本不参与，
# 测不出收益。数字题含具体数值 → 必然 full_read。

QUESTIONS = [
    # ── summary 类（库级概览）：6 道，覆盖全部 6 个文件 ──
    {"id": "s1", "kind": "summary", "covers": "all",
     "query": "请介绍一下这批文件"},
    {"id": "s2", "kind": "summary", "covers": "all",
     "query": "概述一下这些文件"},
    {"id": "s3", "kind": "summary", "covers": "all",
     "query": "请总结这批文件"},
    {"id": "s4", "kind": "summary", "covers": "all",
     "query": "介绍一下这批文件讲了什么"},
    {"id": "s5", "kind": "summary", "covers": "all",
     "query": "请介绍一下这些文件的内容"},
    {"id": "s6", "kind": "summary", "covers": "all",
     "query": "概览这批文件"},

    # ── locate 类（库级定位，每道指向一个文件的独有内容）：6 道 ──
    {"id": "l1", "kind": "locate", "covers": ["quotation"],
     "query": "哪些文件里有打版相关的内容"},
    {"id": "l2", "kind": "locate", "covers": ["ces_table"],
     "query": "哪些文件里谈到了 CES 展会"},
    {"id": "l3", "kind": "locate", "covers": ["crm_big"],
     "query": "哪些文件里有首页和基本设置表"},
    {"id": "l4", "kind": "locate", "covers": ["perf_stats"],
     "query": "哪些文件里记录了季度合计"},
    {"id": "l5", "kind": "locate", "covers": ["cold_email_docx"],
     "query": "哪些文件里谈到了开发信"},
    {"id": "l6", "kind": "locate", "covers": ["negotiation_docx"],
     "query": "哪些文件里谈到了商务谈判"},

    # ── 具体数字题：每文件 1 道，必然 full_read ──
    {"id": "n1", "kind": "number", "covers": ["quotation"],
     "query": "这份报价单的总计金额是多少元？", "expect_number": "39703"},
    {"id": "n2", "kind": "number", "covers": ["ces_table"],
     "query": "产品表里曝光 198070 的那行，点击率是多少？"},
    {"id": "n3", "kind": "number", "covers": ["crm_big"],
     "query": "客户跟进管理系统里的合计客户数是多少？"},
    {"id": "n4", "kind": "number", "covers": ["perf_stats"],
     "query": "个人业绩统计表里一月份的实际业绩是多少美元？"},
    {"id": "n5", "kind": "number", "covers": ["cold_email_docx"],
     "query": "文档里提到一个月可以发多少封开发信？"},
    {"id": "n6", "kind": "number", "covers": ["negotiation_docx"],
     "query": "文档里提到当场给了多少美元的现场打样和小批试单？"},
]

# 改数验证用的题目（问的正是被改的那个字面值）
MUTATION_QUESTION = "这份报价单的报价单号是多少？"

_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

# 沙箱配置改动说明（写进结果 JSON 与报告）
_SANDBOX_NOTES: dict = {}


def _extract_numbers(text: str) -> list[str]:
    """从答案里抽出数字（去千分位逗号），用于数字题逐字比对。"""
    return [m.group(0).replace(",", "") for m in _NUMBER_RE.finditer(text or "")]


def _numbers_equal(left: str, right: str) -> bool:
    """两个答案的数字集合是否一致（顺序不敏感）。"""
    return sorted(_extract_numbers(left)) == sorted(_extract_numbers(right))


def _digest(path: Path) -> str:
    """计算文件 SHA-256（与 agentbase/doc_cache.py 的 file_sha256 同口径）。"""
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prepare_isolated_home() -> Path:
    """建临时 AGENT_HOME 并返回其路径。

    必须在 import agentbase.* 之前设好，否则 agentbase.database 会连到真实 agentbase.db。
    """
    import tempfile

    base = Path(tempfile.mkdtemp(prefix="bench-agentbase-home-"))
    (base / "data").mkdir(parents=True, exist_ok=True)
    os.environ["AGENT_HOME"] = str(base)
    # 明确关闭懒加载重启（bootstrap 内部也会设，这里双保险）
    os.environ["HERMES_DISABLE_LAZY_INSTALLS"] = "1"
    return base


def _prepare_agent_home(home: Path) -> dict:
    """把 Hermes 的配置/凭据/skills 复制进隔离的 AGENT_HOME，并在副本上改开关。

    为什么 agentbase 不需要（也不能）改用户真实的 `~/.hermes`：
    `agentbase/bootstrap.py` 把 **AGENT_HOME 直接当成 HERMES_HOME** 用
    （实测 `get_hermes_home()` 返回 AGENT_HOME），所以 Hermes 的 model / provider /
    skills 全从 AGENT_HOME 下读。把副本放进去即可完全隔离，
    用户真实的 `~/.hermes/config.yaml` 一个字都不用动。

    复制内容：`config.yaml`（模型/开关）、`.env`（API Key）、`auth.json`（凭据）、
    `skills/`（**复制**，不是 symlink —— curator 会往里写）。
    不复制：sessions / memories / backups（避免任何历史与记忆混入）。

    副本上改的开关与 trade 版一致（background_review / MOA / max_turns / MCP），
    理由见 trade 版同名函数。
    """
    import shutil

    import yaml

    real_home = Path.home() / ".hermes"
    notes: dict = {}
    home.mkdir(parents=True, exist_ok=True)

    for name in ("config.yaml", ".env", "auth.json"):
        src = real_home / name
        if src.is_file():
            shutil.copy2(src, home / name)

    src_skills = real_home / "skills"
    dst_skills = home / "skills"
    if src_skills.is_dir() and not dst_skills.is_dir():
        shutil.copytree(src_skills, dst_skills)

    config_path = home / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"找不到 Hermes 配置可复制：{real_home / 'config.yaml'}")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    data.setdefault("auxiliary", {}).setdefault("background_review", {})["enabled"] = False
    notes["auxiliary.background_review.enabled"] = False
    data.setdefault("moa", {})["enabled"] = False
    notes["moa.enabled"] = False
    agent = data.setdefault("agent", {})
    notes["agent.max_turns"] = f"{agent.get('max_turns')} → 30"
    agent["max_turns"] = 30
    for name, block in (data.get("mcp_servers") or {}).items():
        if isinstance(block, dict):
            block["enabled"] = False
            notes[f"mcp_servers.{name}.enabled"] = False

    config_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
    _SANDBOX_NOTES.update(notes)
    return notes


def _bootstrap_runtime() -> None:
    """准备 Hermes 运行环境（与生产启动同一顺序）。

    顺序不能换：先 prepare_hermes_import_paths（sys.path + pm 激活恢复），
    再 load_env_and_set_yolo（要 import hermes_cli）。
    """
    sys.path.insert(0, str(REPO_ROOT))
    from agentbase import bootstrap

    bootstrap.prepare_hermes_import_paths()
    bootstrap.load_env_and_set_yolo()


def _copy_document_set(target_dir: Path) -> list[dict]:
    """把文档集复制进临时文档库目录（内容不变 → SHA256 不变）。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for doc in DOCUMENTS:
        source = DOC_SOURCE_ROOT / doc["rel"]
        if not source.is_file():
            raise FileNotFoundError(f"文档集缺文件：{source}")
        target = target_dir / doc["name"]
        shutil.copy2(source, target)
        copied.append({**doc, "path": str(target), "sha256": _digest(target)})
    return copied


def _read_usage(conn, workspace_id: int) -> list[tuple]:
    """读 usage_ledger 的全部行（按时间排序）。"""
    try:
        return list(conn.execute(
            "SELECT ts, prompt_tokens, completion_tokens, model FROM usage_ledger "
            "WHERE workspace_id = ? ORDER BY ts", (workspace_id,)
        ))
    except Exception:
        return []


def _read_cache_rows(conn, tenant: str) -> dict:
    """读该租户的文档缓存行（键 = sha256）。"""
    try:
        rows = conn.execute(
            "SELECT sha256, extraction_status, doc_kind, attempts, extracted_at, "
            "error_code, summary_text FROM doc_extractions WHERE tenant_id = ?",
            (tenant,),
        ).fetchall()
    except Exception:
        return {}
    return {
        row[0]: {
            "extraction_status": row[1],
            "doc_kind": row[2],
            "attempts": row[3],
            "extracted_at": row[4],
            "error_code": row[5],
            "summary_text": row[6] or "",
        }
        for row in rows
    }


def _usage_delta(before: list, after: list) -> dict:
    """usage_ledger 的增量统计。"""
    new_rows = after[len(before):]
    return {
        "agent_calls": len(new_rows),
        "prompt_tokens": sum(int(r[1] or 0) for r in new_rows),
        "completion_tokens": sum(int(r[2] or 0) for r in new_rows),
        "models": sorted({str(r[3]) for r in new_rows if r[3]}),
    }


def _cache_delta(before: dict, after: dict) -> dict:
    """文档缓存的增量统计：抽取调用次数（attempts 增量）与各文件分类。"""
    attempts = 0
    per_file = {}
    for sha, row in after.items():
        old = before.get(sha)
        old_attempts = int(old["attempts"]) if old else 0
        delta = int(row["attempts"]) - old_attempts
        if delta > 0:
            attempts += delta
        per_file[sha] = {
            "extraction_status": row["extraction_status"],
            "doc_kind": row["doc_kind"],
            "attempts": row["attempts"],
            "attempts_delta": delta,
            "extracted_at": row["extracted_at"],
            "error_code": row["error_code"],
            "summary_chars": len(row["summary_text"]),
        }
    return {"extraction_calls": attempts, "files": per_file}


async def _ask(agentbase_chat, chat_request_cls, query: str, workspace_id: int) -> dict:
    """调生产同步聊天端点一次，返回 {ok, response, cache_context, error}。

    429（每分钟 20 次限流）→ 退避重试；其余异常如实记录，不中断基准。
    """
    # agentbase 的 chat 端点**不写 usage_ledger**（实测跑 5 题全部 0/0），
    # 所以 token 只能从 agent 实例上取。`agentbase/api/chat.py` 是模块级
    # `from ...helpers import create_agent`，包装模块属性即可截到每个实例。
    import agentbase.api.chat as _chat_module

    captured: list = []
    original_create = _chat_module.create_agent

    def _capturing_create_agent(*a, **kw):
        agent = original_create(*a, **kw)
        captured.append(agent)
        return agent

    _chat_module.create_agent = _capturing_create_agent
    try:
        return await _ask_inner(agentbase_chat, chat_request_cls, query,
                                workspace_id, captured)
    finally:
        _chat_module.create_agent = original_create


async def _ask_inner(agentbase_chat, chat_request_cls, query: str, workspace_id: int,
                     captured: list) -> dict:
    """真正发起请求；返回时带上被包装到的 agent 实例的 token 统计。"""
    from fastapi import HTTPException

    for attempt in range(4):
        try:
            payload = chat_request_cls(query=query)
            result = await agentbase_chat(payload=payload, cid=workspace_id)
            return {
                "ok": True,
                "response": result.get("response", ""),
                "cache_context": result.get("analysis_cache_context") or [],
                "analysis_incomplete": bool(result.get("analysis_incomplete")),
                "error": "",
                "tokens": _agent_tokens(captured),
            }
        except HTTPException as exc:
            if exc.status_code == 429 and attempt < 3:
                # 限流：等一个窗口再问
                await asyncio.sleep(62)
                continue
            return {"ok": False, "response": "", "cache_context": [],
                    "analysis_incomplete": False,
                    "error": f"HTTP {exc.status_code}: {exc.detail}"}
        except Exception as exc:  # noqa: BLE001 — 基准要如实记下失败原因
            return {"ok": False, "response": "", "cache_context": [],
                    "analysis_incomplete": False,
                    "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": False, "response": "", "cache_context": [],
            "analysis_incomplete": False, "error": "retries exhausted"}


def _agent_tokens(agents: list) -> dict:
    """把本轮创建的 agent 实例的 session token 计数加起来。

    Hermes 的 `session_prompt_tokens` 是该实例的累计值；每个请求新建实例，
    所以求和即本次请求用量（重试各算各的）。字段缺失时记 0。
    """
    prompt = completion = 0
    for agent in agents:
        prompt += int(getattr(agent, "session_prompt_tokens", 0)
                      or getattr(agent, "session_input_tokens", 0) or 0)
        completion += int(getattr(agent, "session_completion_tokens", 0)
                          or getattr(agent, "session_output_tokens", 0) or 0)
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "agent_calls": len(agents)}


def _append_jsonl(path: Path, payload: dict) -> None:
    """追加一行 JSON（增量落盘：跑一半被打断也不丢已跑的结果）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()


async def _run_questions(agentbase_chat, chat_request_cls, questions, workspace_id,
                         documents, rounds, pause, jsonl_path: Path | None = None,
                         phase: str = "", skip: set | None = None) -> list[dict]:
    """跑若干轮问题，返回每题每轮的记录（同时增量写 JSONL）。"""
    from agentbase.database import get_connection
    from agentbase.doc_scope import detect_request_scope

    results = []
    skip = skip or set()
    for round_index in range(1, rounds + 1):
        for question in questions:
            if (phase or f"round{round_index}", round_index, question["id"]) in skip:
                print(f"  [{phase or round_index}] {question['id']} 已完成，跳过", flush=True)
                continue
            conn = get_connection()
            try:
                usage_before = _read_usage(conn, workspace_id)
                cache_before = _read_cache_rows(conn, str(workspace_id))
            finally:
                conn.close()

            scope = detect_request_scope(question["query"])
            started = time.time()
            answer = await _ask(agentbase_chat, chat_request_cls, question["query"],
                                workspace_id)
            elapsed = round(time.time() - started, 2)

            conn = get_connection()
            try:
                usage_after = _read_usage(conn, workspace_id)
                cache_after = _read_cache_rows(conn, str(workspace_id))
            finally:
                conn.close()

            hit_names = list(answer["cache_context"])
            # 缓存旁路只对 summary 生效：locate 命中缓存后仍全文读
            # （agentbase/api/chat.py:479 会把 skip_paths 清空）。
            full_read = not (scope == "summary" and hit_names)
            usage = _usage_delta(usage_before, usage_after)
            if not usage["prompt_tokens"] and not usage["completion_tokens"]:
                # agentbase 不记账：回退到 agent 实例计数，并标明口径
                usage = {**answer.get("tokens", {}), "models": [],
                         "source": "agent_session"}

            record = {
                "phase": phase or f"round{round_index}",
                "round": round_index,
                "id": question["id"],
                "kind": question["kind"],
                "covers": question["covers"],
                "query": question["query"],
                "scope_detected": scope,
                "ok": answer["ok"],
                "error": answer["error"],
                "elapsed_sec": elapsed,
                "response": answer["response"],
                "cache_context": hit_names,
                "used_cache": bool(hit_names),
                "full_read": full_read,
                "analysis_incomplete": answer["analysis_incomplete"],
                "usage": usage,
                "cache": _cache_delta(cache_before, cache_after),
            }
            results.append(record)
            # 增量落盘：跑一半被超时打断，已跑的结果仍然可用
            if jsonl_path is not None:
                _append_jsonl(jsonl_path, record)
            print(f"  [{record['phase']}] {question['id']} scope={scope} "
                  f"full_read={full_read} hit={len(hit_names)} "
                  f"tokens={record['usage']['prompt_tokens']}"
                  f"/{record['usage']['completion_tokens']} "
                  f"{elapsed}s", flush=True)
            # 题间留间隔，别把每分钟 20 次的限流打满
            await asyncio.sleep(pause)
    return results


def _mutate_quotation(path: Path, old_value: int, new_value: int) -> bool:
    """改掉报价单里的一个**字面数值单元格**（zip 层改 XML）。

    选 `M6`（报价单号 2018123）：它是普通字面值，不是公式结果。
    改它不会让文档自相矛盾 —— 若改合计（`M30` 是 `=SUM(M20:M29)`），
    只改缓存值会让明细与合计对不上，模型会先指出矛盾再复算，
    那验证的就不是「答案跟着内容变」而是「模型怎么处理矛盾」。

    为什么不用 openpyxl：**用它保存会把整册的公式缓存值全部丢掉**，
    之后 `doc_extract`（`data_only=True`）读到的合计数会变成 None。

    改完用 `parse_document` 复核：旧值必须消失、新值必须出现。
    """
    import re
    import zipfile

    target = "xl/worksheets/sheet1.xml"
    with zipfile.ZipFile(path) as src:
        items = [(info, src.read(info.filename)) for info in src.infolist()]

    changed = False
    rewritten = []
    for info, data in items:
        if info.filename == target:
            text = data.decode("utf-8")
            # 只改 M6 单元格内的字面值，避免误伤别处同样的数字
            pattern = re.compile(
                r'(<c r="M6"[^>]*>\s*)<v>' + str(old_value) + r"(</v>)"
            )
            text, count = pattern.subn(rf"\g<1><v>{new_value}\g<2>", text)
            if count:
                changed = True
            data = text.encode("utf-8")
        rewritten.append((info, data))

    if not changed:
        return False

    # 重建 zip（保持原有条目顺序）
    tmp = path.with_suffix(".mutated")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info, data in rewritten:
            dst.writestr(info, data)
    tmp.replace(path)
    return True


def _restore_quotation(original_path: Path, work_path: Path) -> bool:
    """把报价单恢复成原文件（改数验证后必须还原）。"""
    shutil.copy2(original_path, work_path)
    return True


def _reuse_home(path: str) -> Path:
    """复用上次的临时 AGENT_HOME（断点续跑：缓存状态与数据库都保留）。"""
    home = Path(path)
    if not (home / "data").is_dir():
        raise FileNotFoundError(f"续跑目录不存在或不是基准目录：{home}")
    os.environ["AGENT_HOME"] = str(home)
    os.environ["HERMES_DISABLE_LAZY_INSTALLS"] = "1"
    return home


def _reuse_state(home: Path) -> dict | None:
    """读断点续跑状态（公司/库/文档集都复用，避免重建导致缓存键全变）。"""
    state_path = home / "bench-state.json"
    if not state_path.is_file():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def _save_state(home: Path, payload: dict) -> None:
    """写断点续跑状态。"""
    (home / "bench-state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _done_keys(jsonl_path: Path) -> set[tuple]:
    """已完成的 (phase, round, id) 三元组，用于跳过。"""
    done: set[tuple] = set()
    if not jsonl_path.is_file():
        return done
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        done.add((record.get("phase"), record.get("round"), record.get("id")))
    return done


async def _amain(args) -> dict:
    """基准主流程。"""
    home = _reuse_home(args.home) if args.home else _prepare_isolated_home()
    print(f"[bench] 隔离 AGENT_HOME: {home}", flush=True)

    # 配置全部落在隔离的 AGENT_HOME 副本里 —— 用户真实的 ~/.hermes 不动
    sandbox_notes = _prepare_agent_home(home)
    print(f"[bench] 已隔离并把开关写进副本：{sandbox_notes}", flush=True)

    _bootstrap_runtime()

    from agentbase import database
    from agentbase import workspace as workspace_module
    from agentbase.api.chat import app as agentbase_chat
    from agentbase.api.models import ChatRequest
    from agentbase.doc_cache import EXTRACTOR_VERSION
    from agentbase.doc_scope import detect_request_scope

    database.init_db()
    chat_request_cls = ChatRequest

    # 断点续跑：复用上次的公司/库/文档集（重建会让缓存键与进度全部作废）
    state = _reuse_state(home) if args.home else None
    if state:
        workspace_id = int(state["workspace_id"])
        documents = state["documents"]
        print(f"[bench] 断点续跑：复用工作区 {workspace_id}", flush=True)
    else:
        workspace = workspace_module.create("基准测试工作区", slug="bench-doc-cache")
        workspace_id = int(workspace["id"])
        docs_dir = Path(BENCH_DOCS_DIR)
        if docs_dir.exists():
            shutil.rmtree(docs_dir)
        documents = _copy_document_set(docs_dir)

    selected = [d for d in documents
                if not args.only or d["key"] in set(args.only)]
    questions = []
    for q in QUESTIONS:
        if args.only and q["covers"] != "all" and not (set(q["covers"]) & set(args.only)):
            continue
        questions.append({**q, "query_raw": q["query"],
                          "query": f"{q['query']} {BENCH_DOCS_DIR}"})

    print(f"[bench] 文档 {len(selected)} 个 / 问题 {len(questions)} 道 / "
          f"EXTRACTOR_VERSION={EXTRACTOR_VERSION}", flush=True)

    scope_preview = {q["id"]: detect_request_scope(q["query"]) for q in questions}

    # 落状态文件（续跑用）
    _save_state(home, {
        "workspace_id": workspace_id,
        "documents": documents,
    })

    jsonl_path = Path(args.out).with_suffix(".jsonl")
    done = _done_keys(jsonl_path) if args.home else set()
    if args.mutation_only:
        # 只补跑改数验证（正文两轮已完成）
        rounds = []
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("phase") == "main":
                rounds.append(record)
    else:
        rounds = await _run_questions(agentbase_chat, chat_request_cls, questions,
                                      workspace_id, documents, args.rounds, args.pause,
                                      jsonl_path=jsonl_path, phase="main", skip=done)

    # ── 改数验证：问同一题 → 改数字 → 再问 → 改回 → 再问 ──
    mutation = {"question": MUTATION_QUESTION}
    quotation = next(d for d in documents if d["key"] == "quotation")
    original_path = DOC_SOURCE_ROOT / quotation["rel"]
    work_path = Path(quotation["path"])
    mutation_q = [{"id": "m1", "kind": "number", "covers": ["quotation"],
                   "query": f"{MUTATION_QUESTION} {BENCH_DOCS_DIR}"}]

    if args.mutation_only:
        baseline = []
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("phase") == "before" and record.get("id") == "m1":
                baseline = [record]
                break
    else:
        baseline = []

    if not baseline:
        baseline = await _run_questions(
            agentbase_chat, chat_request_cls, mutation_q, workspace_id,
            documents, 1, args.pause, jsonl_path=jsonl_path, phase="before")

    mutation["answer_before"] = baseline[0]["response"] if baseline else ""
    mutation["numbers_before"] = _extract_numbers(mutation["answer_before"])
    mutation["sha256_before"] = _digest(work_path)
    mutation["mutated_to"] = QUOTATION_MUTATED_TOTAL
    changed = _mutate_quotation(work_path, QUOTATION_ORIGINAL_TOTAL,
                                 QUOTATION_MUTATED_TOTAL)
    mutation["mutated"] = changed
    mutation["sha256_after_mutate"] = _digest(work_path) if changed else ""

    if changed:
        mutated_rounds = await _run_questions(
            agentbase_chat, chat_request_cls, mutation_q, workspace_id,
            documents, 1, args.pause, jsonl_path=jsonl_path, phase="mutate")
        mutation["answer_after"] = mutated_rounds[0]["response"]
        mutation["numbers_after"] = _extract_numbers(mutation["answer_after"])
        mutation["round_after"] = mutated_rounds[0]
        _restore_quotation(original_path, work_path)
        restored_rounds = await _run_questions(
            agentbase_chat, chat_request_cls, mutation_q, workspace_id,
            documents, 1, args.pause, jsonl_path=jsonl_path, phase="restore")
        mutation["answer_restored"] = restored_rounds[0]["response"]
        mutation["numbers_restored"] = _extract_numbers(mutation["answer_restored"])
        mutation["round_restored"] = restored_rounds[0]
        mutation["sha256_after_restore"] = _digest(work_path)
        mutation["answer_followed_change"] = (
            str(QUOTATION_MUTATED_TOTAL) in mutation["numbers_after"]
            and str(QUOTATION_MUTATED_TOTAL) not in mutation["numbers_before"]
        )
        mutation["answer_reverted"] = (
            str(QUOTATION_ORIGINAL_TOTAL) in mutation["numbers_restored"]
            and str(QUOTATION_MUTATED_TOTAL) not in mutation["numbers_restored"]
        )
    else:
        mutation["mutated"] = False
        mutation["answer_after"] = ""
        mutation["answer_restored"] = ""
        mutation["answer_followed_change"] = False
        mutation["answer_reverted"] = False

    # ── 最终缓存表快照（分类判定结果）──
    from agentbase.database import get_connection

    conn = get_connection()
    try:
        final_cache = _read_cache_rows(conn, str(workspace_id))
        final_usage = _read_usage(conn, workspace_id)
    finally:
        conn.close()

    by_sha = {d["sha256"]: d for d in documents}
    classification = []
    for sha, row in final_cache.items():
        doc = by_sha.get(sha)
        classification.append({
            "file": doc["name"] if doc else sha[:12],
            "sha256": sha,
            "expect_kind": doc.get("expect_kind") if doc else None,
            "doc_kind": row["doc_kind"],
            "extraction_status": row["extraction_status"],
            "error_code": row["error_code"],
            "attempts": row["attempts"],
            "summary_chars": len(row["summary_text"]),
        })
    classification.sort(key=lambda x: x["file"])

    return {
        "meta": {
            "repo": str(REPO_ROOT),
            "agent_home": str(home),
            "hermes_home_sandbox": str(home),
            "docs_dir": BENCH_DOCS_DIR,
            "sandbox_config_notes": _SANDBOX_NOTES,
            "extractor_version": EXTRACTOR_VERSION,
            "rounds": args.rounds,
            "run_started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "documents": [
                {"key": d["key"], "name": d["name"], "sha256": d["sha256"],
                 "expect_kind": d["expect_kind"], "parse": d["parse"], "role": d["role"]}
                for d in documents
            ],
            "questions": [
                {**q, "scope_detected": scope_preview.get(q["id"])}
                for q in questions
            ],
        },
        "rounds": rounds,
        "mutation": mutation,
        "classification": classification,
        "usage_total": {
            "rows": len(final_usage),
            "prompt_tokens": sum(int(r[1] or 0) for r in final_usage),
            "completion_tokens": sum(int(r[2] or 0) for r in final_usage),
        },
    }


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="文档提取缓存手工基准")
    parser.add_argument("--rounds", type=int, default=2, help="问答轮数（默认 2）")
    parser.add_argument("--only", nargs="*", default=None,
                        help="只跑指定文档 key（默认全部）")
    parser.add_argument("--pause", type=float, default=3.0,
                        help="题间间隔秒数（默认 3，避开每分钟 20 次限流）")
    parser.add_argument("--out", default="reports/benchmark-doc-cache.json",
                        help="结果 JSON 输出路径")
    parser.add_argument("--home", default="",
                        help="断点续跑：复用上次的临时 AGENT_HOME 目录")
    parser.add_argument("--mutation-only", action="store_true",
                        help="只补跑改数验证（复用已有两轮结果）")
    args = parser.parse_args()

    result = asyncio.run(_amain(args))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"[bench] 结果已写入 {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
