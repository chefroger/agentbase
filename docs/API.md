# AgentBase API 参考

AgentBase 的底座能力全部通过 HTTP API 暴露。默认前端只是这些 API 的一个最小壳；
业务前端（含聊天页）应基于本文档另行定制。

- Base URL：`http://127.0.0.1:9120`
- 所有业务/系统 API 前缀：`/api/agentbase`
- 运行中的 OpenAPI：`/openapi.json`；Swagger UI：`/docs`
- 交互式调试：设置页「开发者」→ API 调试控制台，或 `GET /api/agentbase/meta/endpoints`

## 1. 鉴权

### 1.1 Session token

服务每次启动生成随机 token，仅下发给**本机回环**访问的 `/agentbase` 页面：

```bash
TOKEN=$(curl -s http://127.0.0.1:9120/agentbase | sed -n 's/.*let TOKEN = "\([^"]*\)".*/\1/p')
```

请求头：

```
X-Hermes-Session-Token: <TOKEN>
```

- 缺失/错误 → `401`
- token 随服务重启轮换；页面内置的 401 自动恢复会重新获取
- 远程访问页面不会拿到 token（除非显式设置 `AGENTBASE_ALLOW_REMOTE_UI=1`）

### 1.2 Workspace 绑定

需要 workspace 的端点还必须携带：

```
X-Workspace-ID: <id>
```

绑定规则：

1. 当前 session 第一次携带 `X-Workspace-ID` 时会自动绑定到该 workspace；
2. 之后携带**不同** ID 的请求返回 `403`，必须先调用
   `POST /api/agentbase/workspaces/{id}/switch`（该请求的 header 必须等于目标 id）；
3. 列表/创建 workspace、设置、系统、meta 等端点不要求 workspace。

### 1.3 无需鉴权的端点

`GET /agentbase`、`/static/*`、`GET /api/status`、
`GET /api/agentbase/license/status`、`GET /api/agentbase/branding`。

## 2. 错误码

| 状态 | 含义 |
|---|---|
| 400 | 参数不合法 |
| 401 | token 缺失/错误，或 workspace 不存在/未激活 |
| 402 | 许可证过期（chat 端点） |
| 403 | workspace 绑定不匹配 |
| 404 | 资源不存在 |
| 409 | 冲突（重复 workspace、引导已完成、pack 重名） |
| 413 | 上传文件过大 |
| 422 | 请求体校验失败 |
| 429 | 限流（chat 20/min；系统写操作 5/min） |
| 500 | 服务端异常 |

## 3. 端点清单

### 3.1 页面与状态

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/agentbase` | 无（仅回环下发 token） | 底座前端页面 |
| GET | `/api/status` | 无 | 健康、版本、最新版本、`hermes_usable` |
| GET | `/api/agentbase/branding` | 无 | 品牌、业务名、方向、workspace 语义、目录与 onboarding 字段 |

### 3.2 业务配置

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/business/config` | token | 合并后的 business.yaml + 方向预设 |
| PUT | `/api/agentbase/business/config` | token | 原子更新指定字段 |

`PUT` 可写字段：`business_name`、`tagline`、`usage_direction`、
`onboarding_fields`、`branding`、`work_dirs`、`prompt_overrides`、
`workspaces`、`ui`。`skill_pack` 不在此写（走 `/skill-packs/*`）。

```bash
curl -s -X PUT http://127.0.0.1:9120/api/agentbase/business/config \
  -H "X-Hermes-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "usage_direction": "document-analysis",
    "business_name": "文档助手",
    "workspaces": {"term": "项目", "mode": "multi", "create_default": false}
  }'
```

### 3.3 模型、Key 与 Agent 行为

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/settings` | token | providers、默认模型、MoA、agent_behavior、extensions、work_dirs |
| POST | `/api/agentbase/settings/keys` | token | 写 provider Key 到 `~/.agentbase/.env` |
| POST | `/api/agentbase/settings/model` | token | 写默认 provider/model（重启生效） |
| POST | `/api/agentbase/settings/moa` | token | 开/关 MoA（重启生效） |
| GET | `/api/agentbase/models/providers` | token | provider/auth 状态 |

```bash
curl -s -X POST http://127.0.0.1:9120/api/agentbase/settings/keys \
  -H "X-Hermes-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"keys": {"DEEPSEEK_API_KEY": "sk-..."}}'
```

### 3.4 工作区

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/workspaces` | token | 活跃工作区列表 |
| POST | `/api/agentbase/workspaces` | token | 创建工作区（支持 `custom_fields`） |
| GET | `/api/agentbase/workspaces/{id}` | token + workspace | 详情 |
| PUT | `/api/agentbase/workspaces/{id}` | token + workspace | 更新（支持 `custom_fields`） |
| DELETE | `/api/agentbase/workspaces/{id}` | token + workspace + `X-Confirm-Delete: yes` | 软删除 |
| POST | `/api/agentbase/workspaces/{id}/switch` | token | 切换当前 session 绑定 |
| GET | `/api/agentbase/workspaces/{id}/agent-identity` | token + workspace | 读 Agent 身份 |
| PUT | `/api/agentbase/workspaces/{id}/agent-identity` | token + workspace | 写身份（DB + 文件同步） |

```bash
curl -s -X POST http://127.0.0.1:9120/api/agentbase/workspaces \
  -H "X-Hermes-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "项目 A", "custom_fields": {"project_code": "P-1"}}'
```

### 3.5 聊天

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| POST | `/api/agentbase/chat` | token + workspace + license | 同步聊天 |
| POST | `/api/agentbase/chat/stream` | token + workspace + license | SSE 流式聊天 |

请求体：

```json
{"query": "你好", "language": "zh"}
```

> `context` 仅用于历史过滤兼容，底座不依赖它。

### 3.6 对话记录

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/conversations` | token + workspace | 列表（`?limit=50`） |
| GET | `/api/agentbase/conversations/quality-stats` | token + workspace | 评分统计 |
| POST | `/api/agentbase/conversations` | token + workspace | 保存 |
| GET | `/api/agentbase/conversations/{id}` | token + workspace | 单条 |
| PUT | `/api/agentbase/conversations/{id}` | token + workspace | 更新回复 |
| DELETE | `/api/agentbase/conversations/{id}` | token + workspace | 删除 |
| POST | `/api/agentbase/conversations/{id}/rate` | token + workspace | 评分 1–5 |

### 3.7 记忆

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/memory/status` | token | Hindsight 可用性 |
| GET | `/api/agentbase/memory/recall?query=` | token | 长期记忆检索 |

### 3.8 Cron（机器级）

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/cron/today` | token + workspace（值被忽略） | 今日任务 |
| GET | `/api/agentbase/cron/jobs` | token + workspace（值被忽略） | 活跃任务 |
| POST | `/api/agentbase/skills/update` | token + 5/min | 同步 skill 内容 |

### 3.9 文件

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| POST | `/api/agentbase/upload-files` | token + workspace | multipart：`subdir` + `files[]` |

`subdir` 必须是 `business.yaml.work_dirs` 中的目录名；单文件上限 100MB。

### 3.10 Skill 包

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/skill-packs` | token | 已安装包与当前启用项 |
| POST | `/api/agentbase/skill-packs/install` | token | 从本地目录安装 |
| POST | `/api/agentbase/skill-packs/activate` | token | 启用（热加载） |
| DELETE | `/api/agentbase/skill-packs/{name}` | token | 卸载 |

### 3.11 系统

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/system/service-status` | token | 服务运行/自启状态 |
| POST | `/api/agentbase/system/autostart` | token + 5/min | 开/关开机自启 |
| POST | `/api/agentbase/system/quit` | token + 5/min | 退出服务 |
| POST | `/api/agentbase/system/restart` | token + 5/min | 重启服务 |
| POST | `/api/agentbase/system/update` | token + 5/min | 自身更新（独立更新器） |
| GET | `/api/agentbase/system/changelog` | token | 更新说明 |
| POST | `/api/agentbase/system/backup` | token + 5/min | 备份 |
| GET | `/api/agentbase/system/logs` | token | 日志列表；`?name=x.log&lines=200` 读取 |
| GET | `/api/agentbase/system/hermes-compat` | token | Hermes 兼容状态 |
| POST | `/api/agentbase/system/rebuild-venv` | token + 5/min | 重建运行环境 |

### 3.12 许可证

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/license/status` | 无 | 试用/激活状态 |
| POST | `/api/agentbase/license/activate` | token | 激活 |

### 3.13 开发者

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/meta/endpoints` | token | 结构化端点清单（调试控制台使用） |
| GET | `/api/agentbase/meta/api-docs` | token | 本文档 markdown |

### 3.14 首次引导（保留）

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/agentbase/onboarding/status` | token | 是否已完成 |
| POST | `/api/agentbase/onboarding/first-workspace` | token | 创建首个 workspace + 身份 |

> `workspaces.mode=single` 且 `create_default=true` 时启动会自动建默认工作区，
> 因此正常情况下 `first-workspace` 会返回 409。

## 4. SSE 事件（`/chat/stream`）

帧格式：`event: <type>\ndata: <json>\n\n`；每 15 秒发送 `: ping`。

| 事件 | data 字段 |
|---|---|
| `thinking` | `message` |
| `tool_start` | `tool_call_id`, `name`, `args` |
| `tool_complete` | `tool_call_id`, `name`, `result_preview` |
| `analysis_gate` | `status`, `files`, `missing`, `errors`, `skipped`, `coverage_note` |
| `response` | `text`, `elapsed_sec`, `conversation_id` |
| `error` | `message` |
| `done` | `{}`（服务端总会发送；缺失表示连接中断） |

## 5. 调用示例

### 5.1 curl：同步聊天

```bash
curl -s -X POST http://127.0.0.1:9120/api/agentbase/chat \
  -H "X-Hermes-Session-Token: $TOKEN" \
  -H "X-Workspace-ID: $WS" \
  -H "Content-Type: application/json" \
  -d '{"query": "用一句话介绍你自己", "language": "zh"}'
```

### 5.2 Python：SSE 流式

```python
import json, requests

resp = requests.post(
    "http://127.0.0.1:9120/api/agentbase/chat/stream",
    headers={"X-Hermes-Session-Token": token, "X-Workspace-ID": str(ws)},
    json={"query": "你好", "language": "zh"},
    stream=True,
    timeout=1800,
)
event = None
for raw in resp.iter_lines(decode_unicode=True):
    if not raw or raw.startswith(":"):
        continue
    if raw.startswith("event: "):
        event = raw[7:]
    elif raw.startswith("data: ") and event:
        data = json.loads(raw[6:])
        print(event, data)
        if event == "done":
            break
```

### 5.3 JavaScript：fetch + ReadableStream

```js
const resp = await fetch("/api/agentbase/chat/stream", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Hermes-Session-Token": TOKEN,
    "X-Workspace-ID": String(currentWorkspaceId),
  },
  body: JSON.stringify({ query: "你好", language: "zh" }),
});
const reader = resp.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const frames = buffer.split("\n\n");
  buffer = frames.pop();
  for (const frame of frames) {
    const event = /event: (.+)/.exec(frame)?.[1];
    const data = /data: (.+)/.exec(frame)?.[1];
    if (event && data) console.log(event, JSON.parse(data));
  }
}
```

### 5.4 业务配置

```bash
curl -s http://127.0.0.1:9120/api/agentbase/business/config \
  -H "X-Hermes-Session-Token: $TOKEN"
```

### 5.5 安装并启用 skill 包

```bash
curl -s -X POST http://127.0.0.1:9120/api/agentbase/skill-packs/install \
  -H "X-Hermes-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"path": "/absolute/path/to/trade-business-pack"}'

curl -s -X POST http://127.0.0.1:9120/api/agentbase/skill-packs/activate \
  -H "X-Hermes-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "trade-business-pack"}'
```

## 6. 可运行示例

`examples/api/` 下提供与本机服务交互的脚本：

| 脚本 | 说明 |
|---|---|
| `health.py` | 读取 token，调用 status/branding/workspaces |
| `chat_stream.py` | SSE 流式聊天并打印全部事件 |
| `business_config.py` | 读取并修改使用方向/workspace 语义 |
| `packs.py` | 安装/启用/卸载 skill 包 |
| `upload.py` | 上传文件到 work_dirs |

运行：`python examples/api/health.py`（默认 `http://127.0.0.1:9120`）。
