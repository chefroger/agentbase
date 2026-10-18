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

## Phase 7：单文件打包 + 后台常驻服务

**服务模型（方案 A：只跑后端，打开系统浏览器）**

| 入口 | 行为 |
|---|---|
| 双击产物 / 无参数 | `agentbase.opener.open_agentbase()`：探测服务 → 未运行则后台派生 `--service` → 等就绪 → 打开浏览器 |
| `--service` | 前台常驻（uvicorn），由自启机制或双击派生；不打开浏览器 |
| `--stop` | 读 `AGENT_HOME/data/agentbase.pid` → SIGTERM → 等退出 |
| `agentbase open` | 与双击等价（Windows 桌面快捷方式的目标） |

**单实例**：以 `127.0.0.1:9120/api/status` 探活为准；重复启动的服务会因端口冲突退出（app.py 既有重试/退出逻辑）。

**开机自启**

- macOS：launchd `~/Library/LaunchAgents/com.agentbase.assistant.plist`（`RunAtLoad=true`、`KeepAlive=false`，用户级）。`install.sh` 每次重写并 `bootout`+`bootstrap`。
- Windows：计划任务 `AgentBase`（登录触发、`wscript` 隐藏窗口，见 `post_install/win_setup.py`）；install.ps1 与服务启动时幂等确保。
- Linux：systemd user unit（install.sh 既有）。
- 用户偏好：`AGENT_HOME/data/autostart.json`。设置页关闭自启后，Windows 服务重启**不会**把它装回来。
- **安装时必须征得同意**（任务书 §12 红线）：install.sh / install.ps1 会询问；非交互安装（无 tty / 无控制台）默认**不开启**并记录偏好，用户可随时在设置页打开。选择"否"时同时清除旧安装遗留的自启项。

**设置页入口**：`后台服务` 区块（开机自启开关 + 退出服务），对应
`GET /system/service-status`、`POST /system/autostart`、`POST /system/quit`（均需 session token）。

**macOS 产物实测（2026-10-18，本机 x86_64）**

- 构建：`python -m PyInstaller desktop-mac.spec`（PyInstaller 6.22.3）
- 体积 **108MB**（目标 ≤300MB）
- 冷启动到 `/api/status` 就绪：**5.9s**
- 常驻 RSS：**~190MB**（首次加载 provider catalog 后）
- `/agentbase` 返回 200；`/api/agentbase/settings` 能读出 Hermes provider catalog（证明 frozen 下 vendor Hermes import 正常）
- `--stop` 正常停止；无 `ModuleNotFoundError`
- 未签名（PyInstaller 提示需手动签名）

**打包要点（踩坑记录）**

- `vendor/hermes` 以 **datas 源码目录**分发；`bootstrap._adjust_sys_path()` 在 frozen 下把 `_MEIPASS/vendor/hermes` 加入 `sys.path`。只靠 PyInstaller 静态分析会漏 Hermes 的惰性导入。
- Hermes 的运行时依赖必须在 `hiddenimports` 显式列出（ruamel.yaml / certifi / truststore / dotenv / httpx / rich …）；`PIL` 不能排除（Hermes 图像工具需要）。
- 三份 spec（mac/windows/linux）保持一致；`tests/test_service.py::TestSpecHygiene` 钉住"不引用已删模块"和"必须包含 vendor/hermes"。
- 从 trade 原样拷贝的 `pyinstaller.spec` 已删除（产品名含 Foreign、bundle id `com.foreign-agentbase.assistant`、版本 0.3.0、大量死 hiddenimports、永远匹配不到的 b2b skill 循环）；构建正主是 `desktop-*.spec`。

## 自身更新机制（任务书 §12）

**已实现**

- `agentbase/updater/`：`state.py`（`update-state.json` 的 phase / `update.lock` O_EXCL + PID 存活清理）、`changelog.py`、`sources.py`（`GitSource` / `PackageSource`）、`engine.py`（备份 → 换版 → 自检 → 完成/回滚）。
- 自动备份：`AGENT_HOME/data/backups/`，保留最近 5 个；**自动回滚只回滚代码/产物，不回滚用户数据**。
- 独立更新器：`POST /system/update` 只写状态并派生 `update --detached`，随后服务退出；更新器等待旧服务退出（30s SIGTERM → 5s SIGKILL）。
- 半升级恢复：`bootstrap.setup()` 在子命令分发之后、业务初始化之前调用 `recover_if_needed()`；锁存活按 phase 分流，锁死亡派发恢复更新器。
- 更新说明：`CHANGELOG.md`（三份 spec 已打进 bundle）；`GET /system/changelog`；前端更新前弹窗显示说明并要求确认。
- 自检判据：`/api/status` 200 且 `hermes_usable` 为真（status 端点新增该字段）。

**实测**

- 单元测试：`tests/test_updater.py`（24 项）——状态/锁/changelog/PackageSource 替换与回滚/半升级分流/超时升级到 SIGKILL/端点。
- 端到端（源码模式，临时 `AGENT_HOME`）：伪造 `phase=updating` + 死锁 → 重启服务 → 检测半升级、派发恢复、自身退出（exit 0）→ 恢复器写 `rolled_back` 并拉起服务 → `/api/status` 200。日志见 `logs/updater.log`。

**未验证**

- `GitSource` 真实全流程（需要安装到 `~/.agentbase/agentbase` 且有可拉取的新版本）。
- `PackageSource` 真机替换（需要 Windows/macOS 分发包 + manifest）。
- 真实 SIGKILL 超时（单测用假时钟覆盖，未做真机卡死注入）。

## 未完成 / 后续

1. 真·全新机器安装复跑（Windows + macOS）；`install.ps1` 语法验证。
2. 文件上传 → 解析 → Agent 读取全链路真机验证（需要模型 Key）。
3. **Windows 单文件产物未构建**：`desktop-windows.spec` 已就绪，需在 Windows 机器上跑 `scripts/build.ps1` 实测。
4. **macOS 产物仅 x86_64**：本机 Python 为 x86_64；Apple Silicon 需在 arm64 解释器下另构建（任务书允许分别构建）。
5. **代码签名未做**：未签名的常驻/自启程序会触发杀软与 Gatekeeper 提示（任务书已列为产品决策）。
6. **.app 分发包的自启未接线**：当前自启由 install.sh/install.ps1（源码安装）注册；若只分发 .app，需要首次启动时征得用户同意后注册 launchd。
7. `COMPATIBILITY.md` 保留为 Hermes 兼容历史记录（含旧项目名称，属溯源材料）。

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
