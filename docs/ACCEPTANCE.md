# 验收报告（任务书 v2 §9）

基线：`smart-trade-ai@e3f4772`（2026-10-16），pristine 测试 **976 passed / 0 failed**。
证据采集：2026-10-17，本机 macOS（Python 3.14.7，Hermes v0.22.2 vendored）。

| # | 验收项 | 结果 | 证据 / 说明 |
|---|---|---|---|
| 1 | 全新机器 `install.sh` 走通 | ⚠️ **部分** | `install.sh` 语法通过；在本机用临时 `AGENT_HOME` 起服务冒烟通过（`/api/status` ok、页面 200、Hermes 0.22.2 usable）。**未在真·全新机器复跑**；`install.ps1` 因本机无 `pwsh` **未做语法验证** |
| 2 | 零外贸残留 grep | ✅ **通过** | `grep -riE "外贸\|trade\|领英\|linkedin\|b2b\|询盘\|报关\|报价单\|\bPI\b" --include=*.py --include=*.js --include=*.html --include=*.css --include=*.md --include=*.sh --include=*.ps1 agentbase/ static/ skills/ scripts/` → **0 命中**（2026-10-18 审计后补入「报价单/PI」与 `scripts/`，修复 5 处 prompt 残留与安装脚本仓库地址） |
| 3 | 不带 skill 包能启动 | ✅ **通过** | 注册表为空（`skills: []`）；服务正常启动，`/api/status` ok；前端仅提示无业务技能 |
| 4 | `demo-pack` 能被路由命中并调用 | ✅ **通过** | `match_skill("演示一下 demo 技能")` → `demo-skill`；`build_query` 输出含 `[SKILL AUGMENTATION]` 且含 `demo-skill`。真实模型调用需 API Key，未跑 |
| 5 | 第三方 Hermes plugin 加载调用 | ✅ **通过** | `scripts/verify_extensions.py`：在临时 `HERMES_HOME/plugins/` 放插件 → `discover_plugins()` → `tools.registry` 出现 `demo_ping`，调用返回 `pong:ok` |
| 6 | tools registry 注册并调用 | ✅ **通过** | 同一脚本：`get_tool_names_for_toolset("demo")` 返回 `[demo_ping]`，handler 可调用 |
| 7 | 改 `business.yaml` 生效 | ✅ **通过** | 实测：branding 标题/欢迎语、onboarding 字段、prompt override、work_dirs、FastAPI title 全部按配置生效 |
| 8 | 通用测试通过、无僵尸业务测试 | ✅ **通过** | `pytest tests/` → **702 passed / 1 skipped / 0 failed**（2026-10-18，含审计 #11/#12 安全回归）；JS `node --test` → **33 passed**；删除的业务测试已归档在 `docs/EXTRACTED-CAPABILITIES.md` |
| 9 | `FRAMEWORK.md` 完成 | ✅ **通过** | 见 `FRAMEWORK.md`（安装 / 三步接业务 / pack 契约 / 边界 / 数据布局 / Hermes 升级） |

## 额外验证

- **隔离**：刻意传入 `HERMES_HOME=~/.hermes`，bootstrap 强制改写为 `AGENT_HOME`；真实 `~/.hermes` 的 config md5/mtime、plugin md5、目录数与 skills 数前后完全一致。
- **vendor**：93MB / 5,563 文件；`VERSION=0.22.2`；MIT LICENSE 保留；`hermes_cli` / `run_agent` / `AIAgent` import 正常；不创建 pm 托管环境。
- **MCP 客户端**：`scripts/verify_extensions.py` 连接本地 stdio MCP server，注册 5 个工具（`mcp__demo__*`），实际调用 `mcp__demo__echo` 返回 `echo:it-works`。
- **自动升级已删**：`hermes_upgrade.py`、后台钩子、`/system/hermes-upgrade[/stream]` 端点与前端面板全部移除。

## 未完成 / 后续

1. 真·全新机器安装复跑（Windows + macOS）；`install.ps1` 语法验证。
2. 文件上传 → 解析 → Agent 读取全链路真机验证（需要模型 Key）。
3. Phase 7（单文件打包 + 常驻服务）尚未开始。
4. `COMPATIBILITY.md` 保留为 Hermes 兼容历史记录（含旧项目名称，属溯源材料）。

## 审计 bug（任务书 v2 引用的 76c98d1 审计）处置

> 基线说明：实际基线与任务书不同，见 §基线差异。

| # | 审计项 | 状态 |
|---|---|---|
| 1 | 重建脚本 `{sh!r}` 写入 `PosixPath(...)` → 砖机 | ✅ 已修（`shlex.quote` + 回归测试 `TestPosixRebuildScriptPaths`） |
| 3 | Windows launcher 路径少 `local\bin` | ✅ 基线提交 `e3f4772` 已含修复（任务书说的"未修"针对旧基线 76c98d1） |
| 4 | `AGENT_HOME` 定义晚于 venv 块 | ✅ 已修（前移到脚本顶部；venv 跟随 `AGENT_HOME`） |
| 6 | Rosetta 下缺 python3.14 候选 | ✅ 已含（候选 + 版本校验 + Rosetta 拒绝） |
| 7 | launchd label 与 unit 名不一致 | ✅ 一致（`com.agentbase.assistant`） |
| 8 | `_patch_yaml_list` 子串匹配误伤 | ✅ 已修（逐项精确比较 + 回归测试） |
| 10 | 硬编码销毁口令 + 口令进 argv | ✅ 已修（`AGENTBASE_PURGE_PASSWORD` 环境变量 / getpass；拒绝 `--password`） |
| 11 | license 路由无鉴权 / 跨租户 fallback | ✅ 已修：`POST /license/activate` 要求 session token；`GET /license/status` 保持免鉴权（登录前展示品牌）且不再接受 workspace 参数；跨租户读取已消除（license 为机器级）。回归测试 `tests/test_security_hardening.py` |
| 12 | plugin 的 workspace_id 由 LLM 从 system prompt 读取 | ✅ 已修：workspace 由服务端 `bind_workspace()` 在发起 agent 调用时绑定（ContextVar，随 Hermes `propagate_context_to_thread` 传播）；`chat_memory_list` schema 移除 `workspace_id`，handler 只读服务端绑定值并 fail-closed。回归测试 `tests/test_chat_memory_plugin.py` + `TestWorkspaceContextTrust` |

## 基线差异（重要）

| 项 | 任务书写的 | 实际使用 | 原因 |
|---|---|---|---|
| trade 基线 | `76c98d1` | **`e3f4772`** | `e3f4772` 是 `76c98d1` 的**直接后继**（中间恰好 1 个提交），内容正是修复审计 #3 的 Windows launcher 路径。任务书 §10.6 说"76c98d1 上仍未修"——即任务书基线早于该修复。使用 e3f4772 = 使用含修复的最新 main。 |
| 业务 skill 数 | 任务书旧口径 36 / 39 | **38 业务 + 1 框架技能** | trade 共 39 个 skill 目录 = 38 业务（36 个 `b2b-*` + `auto-smtp-email` + `auto-trade-customer-development`）+ `chat-memory`。`auto-smtp-email` 在 pack `registry.yaml` 的 `blocked_skills` 中停用（仅生成草稿，需用户复核），故 **37 个可用业务 skill**。任务书已于 2026-10-18 同步。 |
