# AgentBase

可复用的智能体框架：聊天服务 + skill 路由 + 三层记忆 + Web 面板 + 内置 Hermes 运行时。
框架不含业务 —— 接入新业务只需填 `business.yaml` + 放 skill 包。

**完整文档见 [FRAMEWORK.md](FRAMEWORK.md)**：安装、三步接入新业务、skill pack 契约、目录与数据布局、Hermes 升级流程。

```bash
git clone <agentbase 仓库> agentbase && cd agentbase
bash scripts/install.sh
# Windows: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

默认服务地址：`http://127.0.0.1:9120/agentbase`

- 许可证：AGPL-3.0-only（见 `LICENSE`）
- 内置 Hermes：v0.22.2，MIT，见 `vendor/hermes/LICENSE`
