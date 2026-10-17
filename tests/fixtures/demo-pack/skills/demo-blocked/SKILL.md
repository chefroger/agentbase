---
name: demo-blocked
description: 测试用「被禁用」skill —— 不应被任何匹配路径触发。
when_to_use:
  - "用户提到 blocked"
triggers:
  - blocked
  - 禁用演示
category: test
version: 0.0.1
---

# demo-blocked

测试用 skill，在 registry.yaml 的 `blocked_skills` 里登记，框架不应触发它。
