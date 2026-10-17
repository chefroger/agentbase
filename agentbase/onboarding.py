"""
AgentBase — 首次运行引导模块。

职责：
  首次启动时引导用户完成 workspace 注册和 Agent 身份配置，一步到位。
  提供「一体化」API，将 workspace 创建、agent 身份配置合并为单个原子操作，
  避免用户分两步操作导致状态不完整。

调用方式：
  POST /api/agentbase/onboarding/first-workspace
    Body: {
        "workspace_name": "ABC Trading Co.",
        "contact_name": "张经理",
        "contact_email": "zhang@example.com",
        "agent_identity": {
            "role": "AI 销售助手",
            "products": "工业电机、发电机",
            "differentiation": "源头工厂、价格有竞争力",
            "target_region": "东南亚、欧洲"
        }
    }
    Returns: { "workspace": {...}, "agentbase_workspace": {...} }
"""

from __future__ import annotations

from agentbase import business_config
from agentbase import workspace as _workspace_module
from agentbase.database import get_connection

# ─────────────────────────────────────────────────────────────────────────────
# onboarding state — lightweight in-memory flag to prevent double-triggering
# ─────────────────────────────────────────────────────────────────────────────

# 是否已完成首次引导的全局标志（进程级，非持久化）。
# 服务器重启后归零，不影响用户已创建数据。
# 用途：前端首次打开时检测是否需要显示引导界面。
_onboarding_done: bool = False


def is_onboarding_done() -> bool:
    """检查系统是否已完成首次引导（至少有一家活跃公司）。

    检测逻辑：
      1. 查 workspaces 表是否有 is_active=1 的记录
      2. 如果有 → False（已完成引导，系统已初始化）
      3. 如果没有 → True（需要引导）
    """
    global _onboarding_done
    if _onboarding_done:
        return True

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM workspaces WHERE is_active = 1"
        ).fetchone()
        count = row[0] if row else 0
        _onboarding_done = (count > 0)
        return _onboarding_done
    finally:
        conn.close()


def reset_onboarding_flag() -> None:
    """重置引导标志（用于测试或调试）。"""
    global _onboarding_done
    _onboarding_done = False


# ─────────────────────────────────────────────────────────────────────────────
# Agent identity（由 business.yaml 的 onboarding_fields 动态生成）
# ─────────────────────────────────────────────────────────────────────────────

# 身份模板由 business.yaml 的 onboarding_fields 动态生成 —— 框架里不写死任何业务字段。
def _build_agent_identity(workspace_name: str, identity_data: dict) -> str:
    """根据 onboarding_fields 生成 agent_identity_md 文本。

    identity_data 的键与 business.yaml 里 onboarding_fields[].key 对应；
    未填写的字段如实标注「未填写」，不编造默认业务描述。
    """
    name = workspace_name or "（workspace 名称未设置）"
    lines = [
        f"# Agent 身份配置 — {name}",
        "",
        "## 你是谁",
        "",
        f"你是 {name} 的业务助手。",
        "",
        "## 业务信息",
        "",
    ]
    for field in business_config.onboarding_fields():
        key = str(field.get("key", "")).strip()
        if not key:
            continue
        label = str(field.get("label") or key)
        value = str(identity_data.get(key, "") or "").strip()
        lines.append(f"- **{label}**：{value or '（未填写）'}")

    lines += [
        "",
        "## 沟通原则",
        "",
        "- 专业、简洁、真诚；不编造信息",
        "- 先了解需求，再给方案",
        "- 不确定时明确说明「无法确认」",
        "",
        "## 禁止行为",
        "",
        "- 不编造数据、价格、库存",
        "- 不做无法兑现的承诺",
        "- 不泄露其他 workspace 的信息",
        "",
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# One-step onboarding: 创建公司 + 配置 Agent 身份
# ─────────────────────────────────────────────────────────────────────────────

def create_first_workspace(
    workspace_name: str,
    contact_name: str = "",
    contact_email: str = "",
    identity_data: dict | None = None,
    *,
    work_dir_name: str = "",
) -> dict:
    """创建第一个公司并配置其 Agent 身份（原子操作）。

    参数：
        workspace_name: 公司名称（必填）
        contact_name: 联系人姓名（可选）
        contact_email: 联系人邮箱（可选）
        identity_data: Agent 身份配置字典（可选），
            含 role/products/differentiation/target_region
        work_dir_name: 桌面工作目录名称（目录已存在时用户指定的新名字）

    返回：
        {"workspace": {...}, "agentbase_workspace": {...}}

    异常：
        ValueError: workspace_name 为空，或公司已存在
    """
    if not workspace_name or not workspace_name.strip():
        raise ValueError("workspace_name 不能为空")

    # 构建 agent_identity_md（用模板 + 用户输入填充）
    agent_identity = _build_agent_identity(
        workspace_name.strip(),
        identity_data or {},
    )

    # Step 1: 创建公司记录 + 桌面工作目录 + 文档库
    workspace = _workspace_module.create(
        name=workspace_name.strip(),
        contact_name=contact_name.strip(),
        contact_email=contact_email.strip(),
        work_dir_name=work_dir_name,
    )

    # Step 2: 将 agent_identity_md 写入 agentbase_workspaces（覆盖空值）
    agentbase_workspace = _workspace_module.update_workspace_record(
        workspace_id=workspace["id"],
        agent_identity_md=agent_identity,
    )

    # Step 3: 将 agent_identity 写入公司目录下的标准文件
    # 路径由 agentbase.prompts.write_agent_identity 统一决定（~/.agentbase/{slug}/workspaces/{slug}/agent-identity.md），
    # 这里不自己拼路径 —— 历史上两边各拼一份、拼出不同结果，导致读取方永远读不到写入的文件
    slug = workspace.get("slug", "")
    if slug:
        from agentbase.prompts import write_agent_identity
        write_agent_identity(slug, agent_identity)

    # 更新进程级标志
    global _onboarding_done
    _onboarding_done = True

    return {
        "workspace": workspace,
        "agentbase_workspace": agentbase_workspace,
    }
