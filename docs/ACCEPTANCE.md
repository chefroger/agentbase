# 验收报告（任务书 v2 §9）

基线：`smart-trade-ai@e3f4772`（2026-10-16），pristine 测试 **976 passed / 0 failed**。
证据采集：2026-10-17，本机 macOS（Python 3.14.7，Hermes v0.22.2 vendored）。

| # | 验收项 | 结果 | 证据 / 说明 |
|---|---|---|---|
| 1 | 全新机器 `install.sh` 走通 | ⚠️ **部分** | `install.sh` 语法通过；在本机用临时 `AGENT_HOME` 起服务冒烟通过（`/api/status` ok、页面 200、Hermes 0.22.2 usable）。**未在真·全新机器复跑**；`install.ps1` 因本机无 `pwsh` **未做语法验证** |
| 2 | 零外贸残留 grep | ✅ **通过** | `grep -ri "外贸\|trade\|领英\|linkedin\|b2b\|询盘\|报关" --include=*.py --include=*.js --include=*.html --include=*.css --include=*.md agentbase/ static/ skills/` → **0 命中** |
| 3 | 不带 skill 包能启动 | ✅ **通过** | 注册表为空（`skills: []`）；服务正常启动，`/api/status` ok；前端仅提示无业务技能 |
| 4 | `demo-pack` 能被路由命中并调用 | ✅ **通过** | `match_skill("演示一下 demo 技能")` → `demo-skill`；`build_query` 输出含 `[SKILL AUGMENTATION]` 且含 `demo-skill`。真实模型调用需 API Key，未跑 |
| 5 | 第三方 Hermes plugin 加载调用 | ✅ **通过** | `scripts/verify_extensions.py`：在临时 `HERMES_HOME/plugins/` 放插件 → `discover_plugins()` → `tools.registry` 出现 `demo_ping`，调用返回 `pong:ok` |
| 6 | tools registry 注册并调用 | ✅ **通过** | 同一脚本：`get_tool_names_for_toolset("demo")` 返回 `[demo_ping]`，handler 可调用 |
| 7 | 改 `business.yaml` 生效 | ✅ **通过** | 实测：branding 标题/欢迎语、onboarding 字段、prompt override、work_dirs、FastAPI title 全部按配置生效 |
| 8 | 通用测试通过、无僵尸业务测试 | ✅ **通过** | `pytest tests/` → **689 passed / 1 skipped / 0 failed**；JS `node --test` → **33 passed**；删除的业务测试已归档在 `docs/EXTRACTED-CAPABILITIES.md` |
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
