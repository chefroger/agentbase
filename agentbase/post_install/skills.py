"""
AgentBase — Skills 安装器。

把 skill 复制到 Hermes runtime skills 目录，Hermes 从那里自动发现并注入提示词：

  框架内置：{package}/skills/*/SKILL.md
  业务技能：{skill_pack}/skills/*/SKILL.md

**框架自身只带 chat-memory。** 业务 skill 全部来自当前激活的 skill pack
（见 business.yaml 的 skill_pack 字段）。没有配包时只装框架内置 skill —— 正常降级，
不是错误。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _get_hermes_home() -> Path:
    """解析 Hermes 安装根目录（HERMES_HOME 环境变量 → 平台默认路径）。

    镜像 hermes_constants.get_hermes_home() 实现，避免 import 循环依赖。
    """
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val)  # 显式设置了 HERMES_HOME，直接使用
    if os.name == "nt":
        _local = os.environ.get(
            "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
        )
        return Path(_local) / "hermes"
    return Path.home() / ".hermes"


def _get_trade_home() -> Path:
    """解析 Trade 用户数据目录（AGENT_HOME 环境变量 → 平台默认路径）。

    macOS/Linux: ~/.agentbase/
    Windows:     %LOCALAPPDATA%\\agentbase\\
    """
    val = os.environ.get("AGENT_HOME", "").strip()
    if val:
        return Path(val)
    if os.name == "nt":
        local_appdata = os.environ.get(
            "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
        )
        return Path(local_appdata) / "agentbase"
    return Path.home() / ".agentbase"


def _active_pack_dir() -> Path | None:
    """当前激活的 skill pack 目录（来自 business.yaml / AGENTBASE_SKILL_PACK）。"""
    from agentbase.skill_registry import active_skill_pack

    return active_skill_pack()


def _get_package_skills_dir() -> Path | None:
    """查找已安装 pip 包中的 skills 目录。

    搜索策略（按优先级）：
      1. sys._MEIPASS — PyInstaller 打包模式的临时解压目录
      2. sys.path 中的 trade 包目录（pip install . 场景）
      3. 当前脚本所在目录的父级（pip install -e . 开发模式）

    Returns:
        skills 目录的 Path，找不到时返回 None
    """
    # 策略 0: PyInstaller one-file 模式 — sys._MEIPASS 是临时解压目录
    # desktop.spec 已将 skills/ 打包为 datas，解压后位于 _MEIPASS/skills/
    _meipass = getattr(sys, "_MEIPASS", None)
    if _meipass:
        meipass_skills = Path(_meipass) / "skills"
        if meipass_skills.is_dir():
            return meipass_skills

    # 策略 1: 遍历 sys.path，检查每个路径下是否有 agentbase/__init__.py
    for prefix in list(sys.path):
        p = Path(prefix)
        if not p.is_dir():
            continue
        candidate = p / "agentbase" / "__init__.py"
        if candidate.exists():
            skills_dir = candidate.parent.parent / "skills"
            if skills_dir.is_dir():
                return skills_dir

    # 策略 2: 从本脚本所在路径向上查找（开发模式，本项目根目录）
    self_dir = Path(__file__).parent.parent.parent  # post_install/skills.py → 项目根
    dev_skills = self_dir / "skills"
    if dev_skills.is_dir():
        return dev_skills

    return None


def _copy_skills(src: Path, dst_base: Path, progress_callback=None) -> list[str]:
    """将 src 下的所有 skill 目录复制到 dst_base 对应的 skill 目录。

    每个 skill 在目标创建 dst_base/{name}/SKILL.md。

    **判定标准是「子目录里有 SKILL.md」，不按名字前缀过滤** —— 框架不该知道
    业务 skill 叫什么（旧版写死 b2b-/auto- 前缀，等于把业务知识焊进框架）。

    Args:
        progress_callback: 可选回调 f(msg)，每安装一个 skill 调用一次

    Returns:
        已安装的 skill 目录名列表
    """
    installed = []
    for skill_dir in sorted(src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue

        # 复制 SKILL.md
        dest = dst_base / skill_dir.name / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_file, dest)

        # 同步复制 references/ 子目录（如 qa_pairs.md）
        refs_src = skill_dir / "references"
        if refs_src.is_dir():
            refs_dst = dst_base / skill_dir.name / "references"
            if refs_dst.exists():
                shutil.rmtree(refs_dst)
            shutil.copytree(refs_src, refs_dst)

        installed.append(skill_dir.name)
        if progress_callback:
            progress_callback(f"  ✓ {skill_dir.name}")

    return installed


def _copy_trade_template(src: Path, dst: Path) -> None:
    """将 .agentbase-template/ 目录复制到 Trade 运行时数据目录。

    仅当目标不存在时才复制，避免覆盖用户已有的模板修改。
    同时植入 prompts/system.md 初始提示词文件。

    Args:
        src: 源码中的 .agentbase-template/ 目录
        dst: Trade 运行时目录（~/.agentbase/）
    """
    if src.is_dir():
        dest = dst / ".agentbase-template"
        if not dest.exists():
            shutil.copytree(src, dest, dirs_exist_ok=False)
            for f in dest.rglob("*"):
                if f.is_file() and os.name != "nt":
                    f.chmod(0o644)  # 设置为用户可读写（Windows 不支持 chmod）

    # 植入初始 system prompt（仅当目标不存在时，避免覆盖用户自定义内容）
    prompts_src = src / "prompts" / "system.md"
    prompts_dir = dst / "prompts"
    prompts_dst = prompts_dir / "system.md"
    if prompts_src.is_file() and not prompts_dst.is_file():
        prompts_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prompts_src, prompts_dst)
        if os.name != "nt":
            prompts_dst.chmod(0o644)


# ── 公开 API ──────────────────────────────────────────────────────────────

def install_skills(progress_callback=None) -> None:
    """主入口：将 Trade B2B skills 安装到 Hermes skills 目录。

    调用方式：
      - pip install -e . 或 pip install .（setuptools post-install hook）
      - 手动执行: install-agentbase-skills（pyproject.toml console_scripts）

    Args:
        progress_callback: 可选回调函数 f(msg: str)，用于 PyInstaller wizard 进度报告

    处理流程：
      1. 查找包的 skills 源目录（含 PyInstaller _MEIPASS 支持）
      2. 复制所有 skill 到 ~/.hermes/skills/
      3. 复制 .agentbase-template/ 到 ~/.agentbase/

    Raises:
        SystemExit(1): 找不到 skills 目录或安装失败时
    """
    hermes_home = _get_hermes_home()
    agentbase_home = _get_trade_home()
    hermes_skills_dir = hermes_home / "skills"

    # 查找本地包中的 skills 源目录
    package_skills = _get_package_skills_dir()
    if package_skills is None:
        msg = (
            "[post_install] ERROR: Could not find skills directory.\n"
            f"  _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}\n"
            f"  sys.path: {sys.path[:5]}...\n"
            "  Expected: <package-root>/skills/*/SKILL.md"
        )
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    info = (
        f"[post_install] Hermes home:   {hermes_home}\n"
        f"[post_install] Package skills: {package_skills}\n"
        f"[post_install] Hermes skills: {hermes_skills_dir}"
    )
    if progress_callback:
        progress_callback(info)
    else:
        print(info)

    installed = _copy_skills(package_skills, hermes_skills_dir, progress_callback=progress_callback)

    # 业务 skill 来自当前激活的 skill pack —— 框架自身只带 chat-memory。
    # 没配包（或包不存在）不是错误：照常装框架内置 skill，只是没有业务技能。
    pack_dir = _active_pack_dir()
    if pack_dir is None:
        note = "[post_install] No business skill pack configured — framework skills only."
        (progress_callback or print)(note)
    else:
        pack_skills = pack_dir / "skills"
        if pack_skills.is_dir():
            installed += _copy_skills(pack_skills, hermes_skills_dir, progress_callback=progress_callback)
        else:
            warn = f"[post_install] WARNING: pack {pack_dir} has no skills/ directory."
            print(warn, file=sys.stderr)

    if installed:
        count_msg = f"[post_install] Installed {len(installed)} skills: {', '.join(installed)}"
        if progress_callback:
            progress_callback(count_msg)
        else:
            print(count_msg)
    else:
        warn_msg = "[post_install] WARNING: No skills found to install."
        if progress_callback:
            progress_callback(warn_msg)
        else:
            print(warn_msg, file=sys.stderr)

    # 同时复制 .agentbase-template 到 Trade 运行时数据目录
    template_dir = package_skills.parent / ".agentbase-template"
    if not template_dir.is_dir():
        # PyInstaller _MEIPASS 回退
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            template_dir = Path(meipass) / ".agentbase-template"
    if not template_dir.is_dir():
        # 开发模式回退：从脚本所在目录查找
        template_dir = Path(__file__).parent.parent.parent / ".agentbase-template"

    if template_dir.is_dir():
        template_msg = (
            f"[post_install] Trade home: {agentbase_home}"
        )
        if progress_callback:
            progress_callback(template_msg)
        else:
            print(template_msg)
        agentbase_home.mkdir(parents=True, exist_ok=True)
        _copy_trade_template(template_dir, agentbase_home)
        done_msg = f"[post_install] Trade data template installed to: {agentbase_home}/.agentbase-template"
        if progress_callback:
            progress_callback(done_msg)
        else:
            print(done_msg)

    if progress_callback:
        progress_callback("[post_install] Done.")
    else:
        print("[post_install] Done.")


def update_skills() -> None:
    """更新业务 skill pack，并同步到 Hermes。

    旧实现从 `raw.githubusercontent.com/chefroger/smart-trade-ai` 逐个下载
    b2b 的 SKILL.md —— 抽取之后那套做法已经不成立：skill 现在住在**独立的
    skill pack 仓库**里，而且多半是 private（raw URL 取不到）。

    新实现分三步：
      1. 对当前激活的 skill pack 做一次 `git pull --ff-only`；
      2. 重新加载注册表（skills / blocked_skills）；
      3. 把 pack 的 skills/ 同步进 Hermes skills 目录。

    没有配置包、或包不是 git 检出 → 打印操作指引后正常返回（不算失败）。

    用法: agentbase-skills-update
    """
    pack_dir = _active_pack_dir()

    if pack_dir is None:
        print("[update_skills] 未配置 skill pack（business.yaml 的 skill_pack 为空）。")
        print("  框架内置 skill 随框架一起更新，无需本命令。")
        return

    if not pack_dir.is_dir():
        print(f"[update_skills] skill pack 目录不存在: {pack_dir}", file=sys.stderr)
        sys.exit(1)

    if not (pack_dir / ".git").exists():
        print(f"[update_skills] {pack_dir} 不是 git 检出，无法自动更新。")
        print("  请手动把它替换为最新版 skill pack。")
        return

    print(f"[update_skills] 更新 skill pack: {pack_dir}")

    # 关键：断掉一切交互式提示。撞到凭证提示会永久挂住（这是 Trade 时代
    # 用真机事故换来的教训，见 COMPATIBILITY.md 的网络探测那一节）。
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "never",
    }
    try:
        proc = subprocess.run(
            ["git", "-C", str(pack_dir), "pull", "--ff-only"],
            capture_output=True, text=True, env=env, timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("[update_skills] git pull 超时（120s）——已放弃，不影响当前会话。", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        print(f"[update_skills] git pull 失败：\n{proc.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    print((proc.stdout or "").strip() or "  (已是最新)")

    # 重新加载注册表
    from agentbase.skill_registry import load_active_pack

    count = load_active_pack()
    print(f"[update_skills] 注册表已重载: {count} 个 skill")

    # 同步到 Hermes
    pack_skills = pack_dir / "skills"
    if not pack_skills.is_dir():
        print(f"[update_skills] WARNING: {pack_dir} 下没有 skills/ 目录。", file=sys.stderr)
        return

    hermes_skills_dir = _get_hermes_home() / "skills"
    installed = _copy_skills(pack_skills, hermes_skills_dir)
    print(f"[update_skills] 已同步 {len(installed)} 个 skill 到 {hermes_skills_dir}")
    print("Hermes 会在下一个请求时用上更新后的 skill。")
