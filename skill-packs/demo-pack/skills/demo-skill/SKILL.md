---
name: demo-skill
description: 示例技能 —— 把用户输入整理成结构化摘要，用于验证 skill 包接入链路。
when_to_use:
  - "用户提到「demo」「演示」「示例技能」"
triggers:
  - demo
  - 演示
  - 示例技能
injection_prompt: |
  你是 demo-skill 技能。用户提到 demo/演示时，按以下步骤处理：
  1. 读取用户输入
  2. 输出结构化摘要
category: 示例
version: 0.1.0
author: AgentBase
---

# demo-skill

这是 AgentBase 的示例技能，内容刻意保持中性、无业务含义。

## 步骤

1. 读取用户输入
2. 输出结构化摘要
