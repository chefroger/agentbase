---
name: demo-alpha
description: 测试用技能 alpha —— 输出一段结构化摘要
when_to_use:
  - "用户提到「alpha」「阿尔法」"
triggers:
  - alpha
  - 阿尔法
category: 测试
version: 0.0.1
author: AgentBase
injection_prompt: |
  你是 demo-alpha 技能。用户提到 alpha 时按以下步骤处理：
  1. 读取用户输入
  2. 输出结构化摘要
---

# demo-alpha

这是框架测试用的最小技能，内容刻意保持中性、无业务含义。

## 步骤

1. 读取用户输入
2. 输出一段结构化摘要
