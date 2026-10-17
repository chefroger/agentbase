---
name: demo-beta
description: 测试用技能 beta —— 文档分析
when_to_use:
  - "用户提到「beta」「贝塔」或需要文档分析"
triggers:
  - beta
  - 贝塔
category: 测试
version: 0.0.1
author: AgentBase
injection_prompt: |
  你是 demo-beta 技能。用户提到 beta 或需要文档分析时按以下步骤处理：
  1. 读取文档
  2. 输出分析结果
---

# demo-beta

这是框架测试用的最小技能，覆盖"文档处理类"分支（pack.yaml 的 doc_task_skills）。

## 步骤

1. 读取文档
2. 输出分析结果
