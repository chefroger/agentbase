# AgentBase — 可复用的智能体框架

AgentBase 是一个**只做底座、不含业务**的智能体框架：聊天服务 + skill 路由 + 三层记忆 +
Web 面板 + Hermes 运行时。业务能力全部来自 **skill 包**，接入新业务不用改框架代码。

- 基线来源：`smart-trade-ai@e3f4772`（2026-10-16）抽取
- Hermes：**vendor 固定版本 v0.22.2**（`vendor/hermes/`，MIT，见 `vendor/hermes/README.vendor`）
- 运行数据根：`~/.agentbase/`（`AGENT_HOME`），与用户自己的 `~/.hermes` 完全隔离

---

## 1. 安装

```bash
git clone <agentbase 仓库> agentbase
cd agentbase
bash scripts/install.sh        # macOS / Linux
# Windows: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

安装脚本会：

1. 检查/建立 Python 3.14 运行环境（Hermes 的硬要求）
2. 校验内置 `vendor/hermes/`，安装 `requirements.txt` + `requirements-hermes.txt`
3. 复制 `.agentbase-template/`（首次生成 `~/.agentbase/business.yaml`，已存在则不覆盖）
4. 初始化数据库、注册启动器
5. 启动服务（默认 `http://127.0.0.1:9120/agentbase`）

第一次打开会引导填写 `business.yaml` 里定义的业务字段。

> `hermes-agent` **不需要也不应该**单独安装 —— 源码已随仓库分发。

---

## 2. 接一个新业务：三步

### 第 1 步：填 `~/.agentbase/business.yaml`

```yaml
business_name: "示例业务"
tagline: "一句话介绍"
skill_pack: "skill-packs/demo-pack"     # 业务 skill 包（相对仓库根或绝对路径）

onboarding_fields:                      # 首次引导表单
  - key: role
    label: "助手角色"
    example: "AI 业务助手"

branding:                               # 前端品牌
  title: "示例助手"
  welcome: "你好，我是你的业务助手。"
  logo: ""

work_dirs:                              # 工作目录分类
  - name: documents
    description: "业务文档"

prompt_overrides:                       # 可选：覆盖全局 system prompt
  system: ""
```

### 第 2 步：放 skill 包

把包放进 `skill-packs/<包名>/`（或在设置页「业务技能包」里从本地目录安装）：

```
skill-packs/demo-pack/
  pack.yaml
  registry.yaml
  skills/demo-skill/SKILL.md
  prompts/                # 可选：prompt_overrides
```

### 第 3 步：重启

```bash
agentbase            # 或重新打开桌面图标
```

前端标题、onboarding 表单、system prompt、工作目录、skill 路由全部按新配置生效。

---

## 3. Skill Pack 契约

### 3.1 目录

```
skill-packs/<pack>/
  pack.yaml            # 必需
  registry.yaml        # 路由数据（默认文件名，可由 pack.yaml 的 registry 改）
  skills/<name>/SKILL.md
  prompts/system.md    # 可选：prompt_overrides.system 指向它
  static/              # 预留：业务前端片段（暂不支持）
```

### 3.2 pack.yaml

```yaml
name: demo-pack
version: 0.1.0
description: 一句话说明
registry: registry.yaml

doc_task_skills:        # 需要注入 FULL 提示词（文档生成/分析）的 skill
  - demo-skill

creative_skills:        # 需要更高温度（创意类）的 skill
  - demo-skill

prompt_overrides:       # 可选
  system: prompts/system.md

skills:
  - demo-skill
```

### 3.3 registry.yaml

```yaml
version: 1
blocked_skills: []      # 永不触发的 skill
skills:
  - name: demo-skill
    triggers: [demo, 演示]
    aliases: []
    input_fmt: 用户提供什么
    output_fmt: 用户得到什么
    augment_prompt: |
      命中后注入的指令
```

### 3.4 加载规则

- 启动时读 `business.yaml.skill_pack`；`AGENTBASE_SKILL_PACK` 环境变量可覆盖
- **没有包也能启动**：聊天正常，只是没有业务技能
- `chat-memory` 是框架内置 skill，不走包机制，永远加载
- 一个框架实例只加载**一个**主包

---

## 4. 框架边界

| 属于框架 | 属于业务包 |
|---|---|
| 聊天 / SSE 流式响应 | 具体 skill 的指令与知识库 |
| skill 路由（关键词 + 语义） | 触发词、别名、augment_prompt |
| 三层记忆（对话 / 向量 / 长记忆桥接） | 业务数据模型与业务 API |
| workspace 多租户隔离 | 业务工作目录分类 |
| 文件上传、文档完整性闸门 | 业务文档模板 |
| 设置页（provider / Key / 默认模型 / MoA） | 业务品牌文案 |
| cron 展示（引擎由 Hermes 提供） | 定时任务内容 |
| Hermes vendor + 插件机制 | 第三方插件本身 |

**扩展点（默认一个不删）**：Hermes skills / plugins / MCP 客户端 / tools registry / gateway。

---

## 4.1 扩展点配置与验证

**第三方 plugin**：放到 `~/.agentbase/plugins/<id>/`（`plugin.yaml` + `__init__.py` 的
`register(ctx)`），在 `~/.agentbase/config.yaml` 写：

```yaml
plugins:
  enabled:
    - <id>
```

**MCP server**：写进 `~/.agentbase/config.yaml`：

```yaml
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    enabled: true
```

工具会以 `mcp__<server>__<tool>` 注册进 tools registry。

**一键验证三个扩展点真的能用**：

```bash
PYTHONPATH=vendor/hermes python scripts/verify_extensions.py
```

脚本在临时 `HERMES_HOME` 里跑：加载第三方 plugin → 检查 tools registry 发现 →
连接一个 stdio MCP server 并实际调用。不碰用户数据。

## 4.2 扩展点全量清单（v2 §4.8 盘点）

Hermes 的扩展面远超"skills / plugins / MCP"三项。以下是 vendored v0.22.2 的真实清单。
**默认全部保留**；标 ✅ 的是已经跑通过真实调用的。

### 插件 API（`ctx.register_*`，由第三方 plugin 调用）

| 接口 | 用途 | 状态 |
|---|---|---|
| `register_tool` | 注册工具进 tools registry | ✅ 已验证 |
| `register_hook` | 30+ 生命周期事件（pre/post_tool_call、pre/post_llm_call、stream_*、session_*、approval_*、pre_gateway_dispatch、pre_transcription…） | 保留 |
| `register_middleware` | 按 kind 插入中间件 | 保留 |
| `register_command` / `register_cli_command` | 斜杠命令 / CLI 子命令 | 保留 |
| `register_memory_provider` | 替换记忆后端 | 保留 |
| `register_context_engine` | 替换上下文引擎 | 保留 |
| `register_platform` / `register_telegram_handler` / `register_slack_action_handler` | 消息平台接入 | 保留 |
| `register_auxiliary_task` | 辅助 LLM 任务通道 | 保留 |
| `register_system_prompt_section` | 注入 system prompt 段落 | 保留 |
| `register_automation_blueprint` | 贡献 cron 自动化蓝图 | 保留 |
| `register_source` | 密钥来源 | 保留 |
| `register_redaction_patterns` | 自定义脱敏规则 | 保留 |
| `register_locale` / `register_locale_dir` | 多语言 | 保留 |
| `register_approval_transport` | 审批 UI 传输层 | 保留 |
| `register_dashboard_auth_provider` | 面板登录 | 保留 |
| `ctx.llm` + 能力门控 | provider / model / agent / profile / task override（需 `capabilities` 授权） | 保留 |
| `ctx.platform_actions` | 以 bot 身份操作消息平台（需 `gateway.platform_actions`） | 保留 |

插件能力门控：`tools.override`、`llm.provider_override`、`llm.model_override`、
`llm.agent_id_override`、`llm.profile_override`、`llm.task_override`、`gateway.platform_actions`。
高风险能力需要在 `config.yaml` 的 `plugins.entries.<id>` 显式授权。

### 非插件扩展点

| 接口 | 说明 | 状态 |
|---|---|---|
| Skills（`SKILL.md` 发现） | 任何包/目录都能放 skill | ✅ 已验证（demo-pack） |
| MCP 客户端（`mcp_servers`） | stdio / 远程 MCP server | ✅ 已验证 |
| 内建工具自注册（`vendor/hermes/tools/*.py` 的 `register()`） | 第一方加工具 | 保留 |
| Provider profiles（`providers/base.py`） | 声明式 infer provider | 保留 |
| Gateway 平台（`hermes_platform/`、`gateway/`） | 消息网关与常驻 cron | 保留 |
| Cron 自动化蓝图（`cron/blueprint_catalog.py`） | 内置 + 插件贡献 | 保留 |
| ACP adapter（`hermes acp`） | 编辑器集成协议 | 保留 |
| Web dashboard routers（`hermes_cli/web_routers/`） | Hermes 自带 HTTP API | 保留（agentbase 不直接暴露） |
| Python 包插件（entry points `hermes_agent.plugins`） | pip 安装即加载 | 保留 |

### 资源目录（不是 API，是可直接安装的内容）

| 目录 | 内容 |
|---|---|
| `vendor/hermes/plugin-catalog/` | 可直接安装的第三方插件清单 |
| `vendor/hermes/optional-mcps/` | MCP server 配置目录 |
| `vendor/hermes/optional-skills/` | 可选 skill 目录 |
| `vendor/hermes/plugins/` | Hermes 自带插件 |

### AgentBase 自身的扩展点

| 接口 | 说明 |
|---|---|
| `business.yaml` | 业务名/品牌/onboarding/工作目录/prompt 覆盖 |
| `skill-packs/<pack>/` | 业务 skill 包（registry + SKILL.md） |
| `GET/POST /api/skill-packs` | 本地安装/启用/卸载 pack |
| `GET /api/branding` | 前端品牌 |
| `GET/POST /api/settings` | provider Key / 默认模型 / MoA |
| `static/` | 前端（可替换） |

---

## 5. 目录速览

```
agentbase/
  agentbase/            # 框架 Python 包
    api/                # HTTP 路由（chat / workspace / memory / cron / files / settings / packs）
    workspace/          # 多租户与工作目录
    skill_router.py     # 关键词 + 语义路由
    skill_registry.py   # 从 skill pack 加载注册表
    hermes_compat.py    # Hermes 版本/模型/provider 桥接
    business_config.py  # business.yaml 加载
    pdf_vision.py       # PDF 逐页 vision 判断
  static/               # 前端（app.html / app.js / app.css）
  skills/chat-memory/   # 内置通用 skill
  skill-packs/demo-pack # 示例业务包
  vendor/hermes/        # Hermes v0.22.2 源码快照
  .agentbase-template/  # 首次安装骨架（business.yaml / prompts / workspace 模板）
  tests/                # 框架测试；tests/fixtures/demo-pack/ 为中性测试包
```

---

## 6. 数据与隔离

| 路径 | 内容 |
|---|---|
| `~/.agentbase/business.yaml` | 业务配置（本文件） |
| `~/.agentbase/data/agentbase.db` | 对话 / workspace / 用量 |
| `~/.agentbase/config.yaml` | Hermes 配置（`HERMES_HOME` 指向这里） |
| `~/.agentbase/.env` | provider API Key |
| `~/.agentbase/skills/` | 安装后的 skill 副本 |
| `~/.agentbase/skill-packs/` | 通过设置页安装的包 |
| `~/.agentbase/workspaces/<slug>/` | workspace 数据 |

`HERMES_HOME` **强制等于** `AGENT_HOME`：内置 Hermes 永不读写用户的 `~/.hermes`。

---

## 7. Hermes 升级（手动）

1. `git clone --depth 1 --branch <tag> https://github.com/NousResearch/hermes-agent.git /tmp/hermes-new`
2. 按 `vendor/hermes/README.vendor` 的裁剪清单替换 `vendor/hermes/`
3. 更新 `VERSION` / `README.vendor` / `requirements-hermes.txt`
4. 跑全量测试 + 真机冒烟
5. 提交

没有后台自动升级。
