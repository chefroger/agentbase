# Skill 编写规范

> 适用于任何 skill 包（`skill-packs/<pack>/skills/<name>/SKILL.md`）与框架内置 skill。
> 参考 [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
> 与 [agentskills.io/specification](https://agentskills.io/specification) 的目录结构。

## 目录结构

```
skills/<skill-name>/
  SKILL.md            # 必需：frontmatter + 指令正文
  references/         # 可选：长文档、qa_pairs.md、知识库
  scripts/            # 可选：可执行脚本
  assets/             # 可选：图片等静态资源
```

## SKILL.md frontmatter

```yaml
---
name: demo-skill                 # 必填，与目录名一致，小写字母/数字/连字符
description: 一句话说明这个 skill 做什么、什么时候用
when_to_use:                     # 可选：触发场景描述（给模型看）
  - "用户提到「关键词」"
triggers:                        # 可选：关键词路由用的触发词
  - 关键词
  - keyword
injection_prompt: |              # 可选：命中后注入 system 层的指令（推荐）
  你是 demo-skill 技能……
category: 通用                   # 可选
version: 0.1.0
author: 作者
---
```

规则：

1. `name` 必须与目录名一致；只允许小写字母、数字、连字符。
2. `triggers` 用于关键词路由；同一个词不要出现在多个 skill 里（会互相抢）。
3. `injection_prompt` 是命中后真正注入的文本；没有它时框架回退到注册表里的
   `augment_prompt`。
4. 正文写给模型看的操作步骤，不要写"这是一个 skill"这类元信息。
5. 需要长知识库时放 `references/qa_pairs.md`（格式见下），框架会按相关度检索注入。

## qa_pairs.md 格式

```markdown
## Q1: 问题？
**答案**: 答案正文
**标签**: 标签1, 标签2
**场景**: 什么场景下用
**关键词**: 关键词1, 关键词2
```

## 注册表（pack 级）

`skill-packs/<pack>/registry.yaml` 提供路由所需的完整数据：

```yaml
version: 1
blocked_skills: [被禁用的 skill 名]
skills:
  - name: demo-skill
    triggers: [...]
    aliases: [...]
    input_fmt: 用户应提供什么
    output_fmt: 用户会得到什么
    augment_prompt: |
      命中后注入的指令（injection_prompt 缺失时的回退）
```

## 自检清单

- [ ] frontmatter 是合法 YAML（CRLF 也能解析）
- [ ] `name` 与目录名一致
- [ ] `triggers` 不与其它 skill 冲突
- [ ] `injection_prompt` 或 `augment_prompt` 至少有一个
- [ ] 指令里不写死与本 skill 无关的业务信息
