# AgentBase

可复用的智能体底座：完整 HTTP API + skill 路由 + 三层记忆 + 内置 Hermes 运行时。
默认前端只是底座壳：**分层设置页 + API 调试控制台 + `/dev` 调试聊天**；
业务前端（含聊天主界面）按 [docs/API.md](docs/API.md) 另行定制。

框架不含业务 —— 接入新业务只需填 `business.yaml` + 放 skill 包。

**文档**
- [FRAMEWORK.md](FRAMEWORK.md)：安装、三步接入新业务、skill pack 契约、扩展点、目录与数据布局
- [docs/API.md](docs/API.md)：全部端点、鉴权、SSE 事件与可运行示例
- `examples/api/`：可直接运行的 Python 调用示例

```bash
git clone <agentbase 仓库> agentbase && cd agentbase
bash scripts/install.sh
# Windows: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

默认服务地址：`http://127.0.0.1:9120/agentbase`（设置门户；调试聊天在 `#/dev`）

- 许可证：AGPL-3.0-only（见 `LICENSE`）
- 内置 Hermes：v0.22.2，MIT，见 `vendor/hermes/LICENSE`
