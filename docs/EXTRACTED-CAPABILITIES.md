# 抽取能力清单（P2 收尾）

> 原则（任务书 v2 + GPT 评审建议）：**先记录能力，再删测试**。每一批被删掉的业务测试，
> 都必须在这里留下「它覆盖了什么、现在归谁、是否已验证」。
>
> 基线：`smart-trade-ai@e3f4772`（2026-10-16），pristine 测试 **976 passed / 0 failed**。

---

## 1. 处置总览

| 能力 | 原覆盖位置 | 处置 | 现在归谁 | 状态 |
|---|---|---|---|---|
| 38 个业务 skill（36 `b2b-*` + 2 `auto-*`） | `skills/` | **MOVE** | `trade-business-pack/skills/` | 已移出，339 文件 |
| 业务 skill 注册表（39 条：触发词/别名/augment_prompt） | `agentbase/skill_registry.py` | **MOVE** | `trade-business-pack/registry.yaml` | 已移出，71KB |
| 业务路由断言（哪句话命中哪个 skill） | `tests/test_skill_router_logic.py` 等 | **MOVE → 待补** | trade-business-pack 测试 | ⏳ 待补 |
| Skill 加载 / blocked / QA 对 / CRLF / doc_task | 同上（机制部分） | **KEEP + 改 fixture** | `tests/test_skill_router_blocked.py` 等 | ✅ 56 passed |
| OSINT 模块及其测试 | `agentbase/osint/`、`test_osint_*.py` | **STRIP（P3）** | — | 测试已删，模块待删 |

---

## 2. 迁到 trade-business-pack 的测试覆盖

以下断言不再存在于框架仓库。**它们的内容在 git 历史里**（`agentbase@a79cc4c` 之前），
需要时按 pack 的 skill 名单重新生成：

| 原文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_skill_router_logic.py` | 64 | 中文/英文查询 → 具体 business skill 的路由命中与「不误抢邻居技能」 |
| `tests/test_api.py::TestSkillRouter` | 16 | 同上，经 HTTP 端点验证（含显式 skill 调用、augment_query） |
| `tests/test_osint_cli.py` | 3 | OSINT CLI 的提示词指向 |
| `tests/test_osint_repeat_protocol.py` | 2 | OSINT 重复调用时仍注入完整协议 |
| `tests/test_skill_router_blocked.py`（原版） | 7 | `auto-smtp-email` 被禁用；39 条注册表完整性 |

> **补测位置**：`trade-business-pack/tests/`（尚未建）。建议在 pack 仓库里用
> `AGENTBASE_SKILL_PACK=<pack 根>` 跑真实的业务路由断言。

---

## 3. 保留在框架的机制覆盖（已改用 `tests/fixtures/demo-pack/`）

| 机制 | 测试 | 结果 |
|---|---|---|
| 注册表从 pack 加载（3 条） | `test_skill_router_blocked.py::TestRegistryLoading` | ✅ |
| 无 pack → 空注册表（降级） | 同上 `test_empty_registry_without_pack` | ✅ |
| pack 路径不存在 → 空注册表 | 同上 `test_missing_pack_dir_degrades_to_empty` | ✅ |
| `blocked_skills` 在所有匹配路径生效 | `TestBlockedSkills` | ✅ |
| `pack.yaml` 的 `doc_task_skills` 透出 | `test_pack_manifest_exposes_doc_task_skills` | ✅ |
| QA 对：解析 / 从 pack 加载 / 评分 / 注入 | `TestQAPairs` | ✅ |
| SKILL.md CRLF frontmatter 解析 | `test_skill_frontmatter_crlf.py` | ✅ |
| 文档类任务注入 FULL prompt | `test_document_rules_effects.py` | ✅ |

---

## 4. 抽取期间发现并修复的框架 bug

| # | Bug | 影响 | 修复 |
|---|---|---|---|
| 1 | `skill_router._PRECOMPILED` 在 import 时一次性构建，加载 pack 后不重建 | **装了业务包，路由永远匹配不到**（关键词路由全失效） | 加 `REGISTRY_VERSION`，`_ensure_precompiled()` 按版本重建 |
| 2 | `skill_semantic` 单例索引同理，构建后不感知注册表变化 | 语义检索命中 0 | 同上；显式传入 skills 的实例不联动（测试/调用方自带语料） |
| 3 | `_get_skill_dir()` 只查 `$HERMES_HOME/skills` 和框架自带 `skills/`，不查 pack | pack 里的 `references/qa_pairs.md` 加载不到 | 加 pack 查找路径 |

> 这 3 个 bug 都是「测试只跑单文件时通过、整套跑就失败」的隐藏状态污染 —— 印证了
> 抽取时必须整套跑测试，不能只看单个用例。

---

## 5. 尚未验证的能力（P3–P6 要逐项过）

- [ ] MCP 客户端（任务书 v2 §4.8：连一个公开 MCP server 跑通）
- [ ] 第三方 Hermes plugin 加载调用（§9 验收第 5 条）
- [ ] tools registry 注册新 tool 并被 agent 调用（§9 第 6 条）
- [ ] `demo-pack` 通过真实路由调用（§9 第 4 条）
- [ ] 文件上传 → 解析 → Agent 读取全链路（v2 §4.6）
- [ ] cron 引擎常驻（v2 §12）
