#!/bin/bash
# ==============================================================================
# AgentBase — 一键安装脚本 (macOS / Linux / WSL2)
# ==============================================================================
# 使用方式:
#   curl -fsSL https://raw.githubusercontent.com/chefroger/agentbase/main/scripts/install.sh | bash
#
# 全程使用 venv，不碰系统 Python site-packages，兼容 Homebrew PEP 668。
# ==============================================================================

set -e

# 数据根目录必须在建 venv 之前确定：venv 跟着 AGENT_HOME 走（审计 #4）
AGENT_HOME="${AGENT_HOME:-$HOME/.agentbase}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log_info()  { echo -e "${CYAN}→${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
log_err()   { echo -e "${RED}✗${NC} $*"; }
log_step()  { echo -e "\n${BOLD}════════════════════════════════════════${NC}"; echo -e "${BOLD}$*${NC}"; }

# 克隆或更新一个 git 仓库（失败返回 1，由调用方决定是否中止）。
#
# 为什么要这些判断（都是实测踩出来的）：
#   1. 只有目录**是有效的 git 仓库**（.git 且 HEAD 可解析）才算「已安装」。
#      克隆被网络中断时 git 会留下空目录，旧逻辑 `[ -d ... ]` 会把它当成已装，
#      随后 `git pull` 静默失败、`pip install -e .` 在残缺树里报出误导性错误，
#      而且**重试永远无法恢复**，用户只能手动删目录。
#   2. 用浅克隆 `--depth 1`：全历史克隆在弱网下最慢、最易失败（README 本身就提醒
#      用户要有稳定网络）。跟 main 时本地没有 tag，Hermes 版本推导会退化为「未知」，
#      AgentBase 会打印警告并继续启动，不影响使用；固定版本模式（`--branch <tag>`）
#      会把该 tag 一并带上，版本可正常解出。
#   3. 不吞 git 的 stderr：README 让用户按网络问题排查，看不到真实报错就没法排查。
_clone_or_update() {
    local name="$1" repo="$2" dest="$3" ref="${4:-main}"
    # 目录存在且是有效仓库 → 拉取更新
    if [ -d "$dest/.git" ] && git -C "$dest" rev-parse --verify HEAD >/dev/null 2>&1; then
        # 固定版本模式（ref != main，Hermes 用）：不 pull —— 在 tag 检出上 pull main
        # 会把它拖到 main 尖端，固定就失去意义。已有检出保持原样。
        if [ "$ref" != "main" ]; then
            log_info "已有 $name 检出，保持现状（固定版本 ${ref}，不跟随 main）"
            return 0
        fi
        log_info "更新已有仓库..."
        git -C "$dest" pull --ff-only origin main || log_warn "git pull 失败，继续使用现有代码"
        return 0
    fi
    # 目录存在但不是有效仓库 → 多为上次克隆的残留，重克隆（否则重试永远失败）
    if [ -e "$dest" ]; then
        log_warn "已存在的目录不是有效的代码仓库（上次克隆中断的残留），重新克隆：$dest"
        rm -rf "$dest"
    fi
    mkdir -p "$(dirname "$dest")"
    git clone --depth 1 --branch "$ref" "$repo" "$dest" || {
        log_err "无法克隆 ${name}（git 的报错见上）。请确认网络/VPN 后重新运行本脚本。"
        return 1
    }
    return 0
}

echo ""
echo -e "${BOLD}${CYAN}  AgentBase — 安装向导${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: 检查 Python
# ─────────────────────────────────────────────────────────────────────────────
log_step "Step 1/5: 检查 Python 环境"

# AgentBase 必须跑在 **Python 3.14** 上：Hermes 从 v0.21.6 起只提供 3.14 的依赖集
# （requires-python 里那个 `>=3.11` 只是留给旧安装「跑完自己的升级步骤」的过渡桥），
# 而 AgentBase 是**进程内**嵌 Hermes 的，解释器必须与 Hermes 的托管环境同 ABI。
# 在 3.11~3.13 上会变成「装得上、起不来」，所以这里不再接受 3.11~3.13。
# 隔离铁律：HERMES_HOME 永远等于 AGENT_HOME，绝不指向用户的 ~/.hermes。
# 下面的 Python 搜索因此只看 AgentBase 自己的目录树，不再碰独立 Hermes 的安装。
HERMES_HOME="$AGENT_HOME"

# 判据：这个解释器的版本号**正好**是 3.14（不是「>= 3.11」那种下限写法）
_is_py314() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)' 2>/dev/null
}

_find_python314() {
    local cmd cand
    # 1) PATH 上的解释器（版本号必须正好是 3.14）
    for cmd in python3.14 python3; do
        if command -v "$cmd" &>/dev/null && _is_py314 "$(command -v "$cmd")"; then
            command -v "$cmd"
            return 0
        fi
    done

    # 2) Hermes 自带的托管解释器 —— 优先用它：与 Hermes 的运行时 ABI 完全一致。
    #
    # **刻意不写死布局**。2026-10-15 用户实测：我按代码推断出来的单一 glob
    # （installs/*/environments/*/bin/python）在真机上一个都匹配不到 —— 真实布局有两棵
    # 代际树，且代际里还套一层 venv/（权威来源 pm/operations.py:152/210
    # `generation / "venv"`、pm/install_states.py:72 的两棵树）。
    # 写死布局的 glob 一旦猜错就是「静默找不到」，而且我无法在本机观测真实布局。
    # 所以改成**递归找 + 按版本号验**：对布局变化免疫，多找到的由 _is_py314 兜住。
    # 任一份 3.14 都能用来建 AgentBase 的 venv（同为 cp314 ABI），无需挑特定的那一份。
    #
    # maxdepth 6 刚好到 <tree>/<gen>/venv/bin/python：再深就进 site-packages 了（慢且无益）。
    # 先按「名字就带 3.14」找（无歧义），再按通用名 python/python3 找并逐个验版本。
    # heredoc 而非 `for x in $(...)`：两者都保证在 sh 下能跑，但 heredoc 还保住了
    # 路径里的空格（`$( )` 会按空白拆词，Windows/Git-Bash 下很容易踩）
    while IFS= read -r cand; do
        if [ -x "$cand" ] && _is_py314 "$cand"; then
            echo "$cand"
            return 0
        fi
    done <<EOF
$(find "$HERMES_HOME/installs" "$HERMES_HOME/tools" -maxdepth 6 \
      \( -type f -o -type l \) -name "python3.14" 2>/dev/null | head -400)
EOF
    while IFS= read -r cand; do
        if [ -x "$cand" ] && _is_py314 "$cand"; then
            echo "$cand"
            return 0
        fi
    done <<EOF
$(find "$HERMES_HOME/installs" "$HERMES_HOME/tools" -maxdepth 6 \
      \( -type f -o -type l \) \( -name "python" -o -name "python3" \) 2>/dev/null | head -400)
EOF

    # 3) Homebrew 常见位置（Intel / Apple Silicon）
    for cand in /opt/homebrew/bin/python3.14 /usr/local/bin/python3.14; do
        if [ -x "$cand" ] && _is_py314 "$cand"; then
            echo "$cand"
            return 0
        fi
    done
    return 1
}

PYTHON="$(_find_python314 || true)"

if [ -z "$PYTHON" ]; then
    log_err "需要 Python 3.14，但未找到。"
    echo ""
    echo "  AgentBase 需要 Python 3.14（内置 Hermes 也运行在同一解释器上）。"
    echo "  安装一个 3.14 后重新运行本脚本："
    echo "       macOS:  brew install python@3.14"
    echo "       Ubuntu: sudo apt install python3.14 python3.14-venv"
    exit 1
fi
log_ok "Python $("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')（${PYTHON}）"

# ── 架构检测 + 自动修正（Apple Silicon 兼容性）────────────────────────────
ARCH=$(uname -m)
PY_ARCH=$("$PYTHON" -c "import platform; print(platform.machine())")
if [ "$ARCH" = "arm64" ] && [ "$PY_ARCH" = "x86_64" ]; then
    log_warn "检测到 CPU 是 arm64 (Apple Silicon)，但 Python 是 x86_64 (Rosetta)。"
    log_info "正在搜索原生 arm64 Python ..."

    # 主动搜索原生 arm64 Homebrew Python
    NATIVE_PYTHON=""
    for candidate in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11; do
        if [ -x "$candidate" ]; then
            _arch=$("$candidate" -c "import platform; print(platform.machine())" 2>/dev/null)
            if [ "$_arch" = "arm64" ]; then
                NATIVE_PYTHON="$candidate"
                break
            fi
        fi
    done

    if [ -n "$NATIVE_PYTHON" ]; then
        log_ok "找到原生 arm64 Python: $NATIVE_PYTHON ($("$NATIVE_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"))"
        PYTHON="$NATIVE_PYTHON"
    else
        log_err "未找到原生 arm64 Python。Rosetta Python 会导致 Hermes 不可用。"
        echo ""
        echo "  修复方法："
        echo "    1. 安装原生 Homebrew（如果当前是 Rosetta 版）："
        echo "       /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "    2. 安装原生 Python："
        echo "       brew install python@3.12"
        echo "    3. 重新运行此安装脚本："
        echo "       curl -fsSL https://raw.githubusercontent.com/chefroger/agentbase/main/scripts/install.sh | bash"
        exit 1
    fi
fi

# 反向检查：Intel CPU + arm64 Python（极罕见）
if [ "$ARCH" = "x86_64" ] && [ "$PY_ARCH" = "arm64" ]; then
    log_err "架构不匹配：CPU 是 x86_64 (Intel)，但 Python 是 arm64。"
    echo "  请安装与 CPU 匹配的 Python 版本。"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 创建 venv（所有后续安装都在 venv 内，不碰系统 Python）
# ─────────────────────────────────────────────────────────────────────────────
_VENV_REAL="$AGENT_HOME/venv"
VENV_DIR="$_VENV_REAL"
# 非空 = 旧环境还在原地、新环境建在 .new 里、依赖装完才切换（切换点见 Step 3 末尾）
_VENV_OLD=""

# 已有 venv 但解释器**不是 3.14** → 必须重建。旧装机器就地升级 agentbase 时，代码与依赖
# 都换了、venv 的解释器还是旧的（`agentbase update` 只更新代码与依赖，不重建 venv），
# 于是 Hermes 的 pm 激活会把 cp314 的包塞进旧解释器 → 聊天只报「AI Agent 模块未加载」。
# **重建不会丢任何用户数据**：数据在 $AGENT_HOME 下（数据库、公司目录），不在 venv 里。
if [ -f "$VENV_DIR/bin/python" ] && ! _is_py314 "$VENV_DIR/bin/python"; then
    # 用 % 格式化而不是 f-string：这里跑的是**即将被替换的老解释器**，可能是 3.11
    # （f-string 在 3.12 之前不允许内层用同类引号），写 f-string 会 SyntaxError，
    # 于是这行永远显示「未知」—— 信息白白丢掉。
    _old_ver=$("$VENV_DIR/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "未知")
    log_warn "已有的运行环境是 Python ${_old_ver}，需要 3.14 —— 正在重建（不会动你的数据）..."
    # 换掉之前留一份已装包清单：venv 里可能有用户手动 pip install 的东西，
    # 这份清单是事后唯一的追查线索。失败不影响安装（best-effort）。
    _dump_dir="${AGENT_HOME:-$HOME/.agentbase}"
    mkdir -p "$_dump_dir" 2>/dev/null
    "$VENV_DIR/bin/pip" freeze > "$_dump_dir/venv-packages-before-rebuild.txt" 2>/dev/null \
        && log_info "已把重建前的包清单留档：$_dump_dir/venv-packages-before-rebuild.txt"
    # **不在原地重建**（2026-10-16 改）。原实现是 `rm -rf "$VENV_DIR"` 后立刻重建，于是
    # 中间任何一步失败（断网 / 磁盘满 / 找不到 3.14 / 依赖装不上）都会留下
    # 「旧的已经删了、新的没建成」——用户软件直接打不开，而客群是电脑小白，无力自救。
    # 改为把新环境建到 .new、依赖全部装成功后才切换，失败时旧环境原样可用。
    _VENV_OLD="$VENV_DIR"
    VENV_DIR="${_VENV_REAL}.new"
    # 只清上一次失败残留的 .new —— 它从来不是用户数据，删了不影响任何人
    rm -rf "$VENV_DIR"
fi
if [ ! -f "$VENV_DIR/bin/python" ]; then
    log_info "创建虚拟环境..."
    "$PYTHON" -m venv "$VENV_DIR"
fi
PIP="$VENV_DIR/bin/pip"
PY="$VENV_DIR/bin/python"
log_ok "虚拟环境就绪 ($VENV_DIR)"

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: 检查 Hermes Agent
# ─────────────────────────────────────────────────────────────────────────────
log_step "Step 2/5: Hermes（内置）"

# 任务书 v2 §10.7：Hermes 源码随框架分发在 vendor/hermes/，用户**不需要**单独安装。
# 真正的完整性检查放在 Step 3（clone 完成之后）—— 这一步时仓库还没落地。
#
# 隔离铁律：运行时 HERMES_HOME 固定指向 AGENT_HOME（~/.agentbase），
# vendored Hermes 永不读写用户自己的 ~/.hermes。用户机器上可能已经装着
# 独立 Hermes / OpenClaw，两者互不干扰。
log_ok "Hermes 随 agentbase 内置分发，无需单独安装（版本见 vendor/hermes/VERSION）"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: 安装 agentbase + 全部依赖
# ─────────────────────────────────────────────────────────────────────────────
log_step "Step 3/5: 安装 AgentBase"

AGENTBASE_REPO="https://github.com/chefroger/agentbase.git"
AGENTBASE_DIR="$HOME/.agentbase/agentbase"

# 记录回滚点（2026-10-16 加）。重建场景下依赖若装不上，代码必须能退回升级前 ——
# 否则「新代码 + 旧 venv」照样起不来，等于把「重建失败」升级成「彻底打不开」。
# 新装用户这里是空的（目录还不存在），_rollback_code 自然什么都不做。
_AGENTBASE_HEAD_BEFORE=""
if [ -d "$AGENTBASE_DIR/.git" ] && git -C "$AGENTBASE_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
    _AGENTBASE_HEAD_BEFORE=$(git -C "$AGENTBASE_DIR" rev-parse HEAD)
fi

_rollback_code() {
    [ -z "$_AGENTBASE_HEAD_BEFORE" ] && return 0
    log_warn "正在把代码回退到升级前的版本（${_AGENTBASE_HEAD_BEFORE:0:8}）..."
    git -C "$AGENTBASE_DIR" reset --hard "$_AGENTBASE_HEAD_BEFORE" 2>/dev/null \
        && log_ok "代码已回退，旧版本仍可正常使用" \
        || log_err "代码回退失败 —— 请把上面的输出发给技术支持"
    # 丢弃半成品的新环境；旧环境（$_VENV_OLD）始终没被动过
    [ -n "$_VENV_OLD" ] && rm -rf "$VENV_DIR"
    return 0
}

_clone_or_update "agentbase" "$AGENTBASE_REPO" "$AGENTBASE_DIR" || exit 1

cd "$AGENTBASE_DIR"

# ── 内置 Hermes 完整性检查（clone 到这里之后才能查）──────────────────────
if [ -d "$AGENTBASE_DIR/vendor/hermes/hermes_cli" ]; then
    _VENDOR_VER="$(cat "$AGENTBASE_DIR/vendor/hermes/VERSION" 2>/dev/null || echo unknown)"
    log_ok "内置 Hermes ${_VENDOR_VER}（vendor/hermes，已接管不再跟踪上游）"
else
    log_err "仓库缺少内置 Hermes：vendor/hermes/hermes_cli"
    echo "  仓库不完整，请重新下载/克隆 agentbase。"
    exit 1
fi

# 装依赖：框架自身 + **Hermes 的依赖闭包**（vendor 源码不 pip 安装，但依赖要装）
# 用 if 而非裸命令：`set -e` 会让失败直接退出，跳过代码回滚，机器就卡在
# 「新代码 + 旧依赖」的半吊子状态。
# 用 if 而非裸命令：`set -e` 会让失败直接退出，跳过代码回滚，机器就卡在
# 「新代码 + 旧依赖」的半吊子状态。
if ! "$PIP" install -r requirements.txt; then
    log_err "依赖安装失败（多为网络或磁盘问题）。"
    _rollback_code
    exit 1
fi
if ! "$PIP" install -r requirements-hermes.txt; then
    log_err "Hermes 依赖安装失败（多为网络或磁盘问题）。"
    _rollback_code
    exit 1
fi
if ! "$PIP" install -e "." --no-deps; then
    log_err "agentbase 自身安装失败。"
    _rollback_code
    exit 1
fi

# 可选依赖：客户语义检索用的向量扩展（sqlite-vec）。
# **单独装、失败只警告** —— 它不是主链依赖：不装则语义检索自动降级关键词，
# 其余功能零影响；而个别平台（如 Windows ARM）没有对应 wheel，
# 不能因为一个可选能力让整台机器的安装失败。
if "$PY" -c "import sqlite_vec" 2>/dev/null; then
    log_ok "sqlite-vec 已安装（客户语义检索可用）"
elif "$PIP" install "sqlite-vec>=0.1.6" >/dev/null 2>&1; then
    log_ok "sqlite-vec 安装完成（客户语义检索可用）"
else
    log_warn "sqlite-vec 未安装：客户语义检索将降级为关键词检索（其余功能不受影响）"
fi
cd - >/dev/null

# ─────────────────────────────────────────────────────────────────────────────
# 依赖全部装成功后，才把新运行环境切换到位（对应 Step 1 的 .new 方案）
#
# 为什么把切换放在这里而不是建 venv 时：切换是**唯一不可逆的一步**，把它压到
# 所有可能失败的动作（建 venv、git pull、pip install）之后，失败面就只剩「两个
# 目录改名」——那是本地文件操作，几乎不会失败；即便失败，下面也保留了 .old 供恢复。
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$_VENV_OLD" ]; then
    log_info "新运行环境已就绪，正在切换..."
    rm -rf "${_VENV_OLD}.old"
    if mv "$_VENV_OLD" "${_VENV_OLD}.old" 2>/dev/null && mv "$VENV_DIR" "$_VENV_OLD" 2>/dev/null; then
        rm -rf "${_VENV_OLD}.old"
        VENV_DIR="$_VENV_OLD"
        PIP="$VENV_DIR/bin/pip"
        PY="$VENV_DIR/bin/python"
        log_ok "已切换到 Python 3.14 运行环境"
    else
        # 把旧环境挪回来（.old 是刚才那一步改的名），丢弃半成品
        log_err "切换运行环境失败，正在恢复原环境..."
        [ -d "${_VENV_OLD}.old" ] && mv "${_VENV_OLD}.old" "$_VENV_OLD" 2>/dev/null
        rm -rf "${_VENV_REAL}.new"
        _rollback_code
        exit 1
    fi
fi

log_ok "AgentBase 安装完成"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: 安装内置 skills
# ─────────────────────────────────────────────────────────────────────────────
log_step "Step 4/5: 安装内置 skills"

# 必须用真实存在的入口：此前写的是 `python -m agentbase.post_install install`，
# 但该包**没有 __main__.py** → 这一步从未生效过（报错被 2>/dev/null 吞掉，
# 只打印下面那句警告）。实测新装后 AGENT_HOME 的 skills 目录里 0 个 skill。
if "$PY" -c "from agentbase.post_install import install_skills; install_skills()"; then
    log_ok "内置 skills 安装完成"
else
    log_warn "内置 skills 安装可能不完整（首次启动时会自动同步）"
fi

# chat-memory 插件：agentbase 自带的工具（让 LLM 能用 agentbase.conversations 表查历史对话）。
# setup() 也会兜底同步 + 写 config.yaml，这里做一次显式的初始安装，避免用户装完
# 还没启动 agentbase 之前就看不到工具（虽然通常不实际发生，但稳）。
if "$PY" -c "from agentbase.bootstrap import sync_chat_memory_plugin, ensure_chat_memory_plugin_enabled; sync_chat_memory_plugin(); ensure_chat_memory_plugin_enabled()"; then
    log_ok "chat-memory 插件已部署到 $AGENT_HOME/plugins/chat-memory"
else
    log_warn "chat-memory 插件部署失败（首次启动时会自动重试）"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: 初始化数据目录
# ─────────────────────────────────────────────────────────────────────────────
log_step "Step 5/5: 初始化数据目录"

mkdir -p "$AGENT_HOME/data"
mkdir -p "$AGENT_HOME/workspaces"

"$PY" -c "from agentbase.database import init_db; init_db()" 2>/dev/null && \
    log_ok "数据库初始化完成 ($AGENT_HOME/data/agentbase.db)" || \
    log_info "数据库将在首次启动时自动初始化"

# ─────────────────────────────────────────────────────────────────────────────
# 导出 agentbase 命令到 ~/.local/bin（放 PATH 里）
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/agentbase" << LAUNCHER
#!/bin/bash
export HERMES_HOME="$AGENT_HOME"
# 禁用 Hermes 懒加载重启：否则 agent 创建时会被 exec 到 Hermes 自带的 store python
# （那里没有 agentbase 包），agent 线程以 RelaunchExit(SystemExit) 静默死亡，
# 前端只会看到「Agent 未返回有效回复」。bootstrap.py 里也设了一处，这里是双保险。
export HERMES_DISABLE_LAZY_INSTALLS="1"
exec "$VENV_DIR/bin/python" "$AGENTBASE_DIR/server.py" "\$@"
LAUNCHER
chmod +x "$HOME/.local/bin/agentbase"

# ─────────────────────────────────────────────────────────────────────────────
# 检查 PATH 中是否有 ~/.local/bin
# ─────────────────────────────────────────────────────────────────────────────
if ! echo "$PATH" | tr ':' '\n' | grep -qxF "$HOME/.local/bin"; then
    SHELL_NAME=$(basename "${SHELL:-$SHELL}")
    case "$SHELL_NAME" in
        zsh)  RC_FILE="$HOME/.zshrc" ;;
        bash) RC_FILE="$HOME/.bashrc" ;;
        *)    RC_FILE="$HOME/.profile" ;;
    esac

    if ! grep -qF 'export PATH="$HOME/.local/bin:$PATH"' "$RC_FILE" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 安装后自检（快检：零 token，不发真实请求）
#
# 端到端验活（真发一次对话 / 一张图 / 一次搜索）在**首次启动时**跑 —— 那时服务与
# 配置都已就位，结果会落盘并在界面提示。这里只做能立刻发现「装坏了」的快检，
# 避免安装因为网络波动误报失败而挡住用户。
# ─────────────────────────────────────────────────────────────────────────────
# 两处都必须在调 doctor 之前处理：
#   1. `prepare_hermes_import_paths()` —— Hermes 不再装进 AgentBase 的 venv，不先准备
#      sys.path 就直接 import doctor 会报 `No module named 'run_agent'`（干净机器实测）。
#   2. doctor 自己会 import Hermes，会触发 pm 激活剥离 venv 的 site-packages；
#      那一步的恢复也在这个函数里，漏了会让后面 holehe/sqlite-vec 误报「未安装」。
# 「Hermes 版本」这一项刻意不计入致命项：内置 Hermes 版本随 AgentBase 锁定，用户不需要
# 也不能单独升级（自动升级状态机已删除）。若这里判失败并 exit 1，用户会卡在安装阶段，
# 而不是拿到可操作的提示。
if ! "$PY" -c "import sys; from agentbase.bootstrap import prepare_hermes_import_paths; prepare_hermes_import_paths(); from agentbase.doctor import run_doctor, format_report, has_fatal_failure; r = run_doctor(deep=False); print(format_report(r)); sys.exit(1 if has_fatal_failure(r, ignore_names=('Hermes 版本',)) else 0)"; then
    log_err "自检发现致命问题，安装不完整。请把上面的输出发给技术支持。"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# 完成
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}══ 安装完成 ══${NC}"
echo ""
echo -e "  启动方式:"
echo -e "    新终端: ${BOLD}agentbase${NC}"
echo -e "    当前终端: ${BOLD}$HOME/.local/bin/agentbase${NC}"
echo ""
echo -e "  启动后打开: ${CYAN}http://127.0.0.1:9120/agentbase${NC}"
echo ""
echo -e "  数据位置:"
echo -e "    用户数据: ${CYAN}$AGENT_HOME/${NC}"
echo -e "    Hermes 配置: ${CYAN}$HERMES_HOME/${NC}"
echo ""
echo -e "  帮助: ${CYAN}agentbase --help${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 开机自启需用户确认（任务书 §12：不得偷偷装）
#
# 交互终端问一句；非交互安装（如 curl | bash 且没有 tty）**默认不开启**，
# 并把偏好写成 false —— 用户之后可以在设置页随时打开。
# ─────────────────────────────────────────────────────────────────────────────
_want_autostart() {
    if [ -t 0 ]; then
        printf "  AgentBase 会在登录后自动在后台常驻运行（无窗口）。是否开启开机自启？[Y/n] "
        read -r _ans || return 1
        case "$_ans" in
            [nN]*) return 1 ;;
            *) return 0 ;;
        esac
    fi
    return 1
}

if _want_autostart; then
    WANT_AUTOSTART=1
    # 恢复默认：清掉「用户之前手动关闭自启」的偏好记录
    "$VENV_DIR/bin/python" -c "from agentbase.service import reset_autostart_preference; reset_autostart_preference()" 2>/dev/null || true
else
    WANT_AUTOSTART=0
    # 同时移除旧安装可能留下的自启项（用户明确选择了不开启）
    "$VENV_DIR/bin/python" -c "from agentbase.service import set_autostart; set_autostart(False)" 2>/dev/null || true
    echo -e "  ${YELLOW}已跳过开机自启${NC}（安装完成后可在设置页随时开启）"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 配置 macOS 开机自启动（launchd，后台静默运行，无终端窗口）
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$(uname -s)" == "Darwin" ]] && [ "$WANT_AUTOSTART" = "1" ]; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.agentbase.assistant.plist"
    mkdir -p "$PLIST_DIR"

    # 每次都重写：旧装用户的 plist 可能带 KeepAlive=true，
    # 那样「退出服务」后会被 launchd 立刻拉起（Phase 7 要求可退出）。
    cat > "$PLIST_FILE" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentbase.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOME/.local/bin/agentbase</string>
        <string>--no-browser</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$AGENT_HOME/logs/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$AGENT_HOME/logs/launchd-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HERMES_HOME</key>
        <string>$HERMES_HOME</string>
        <key>AGENT_HOME</key>
        <string>$AGENT_HOME</string>
        <key>PATH</key>
        <string>$VENV_DIR/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
PLIST
    # 确保日志目录存在
    mkdir -p "$AGENT_HOME/logs"
    # 卸载旧配置后再加载（用户级，无需 sudo）
    launchctl bootout gui/$(id -u) "$PLIST_FILE" 2>/dev/null || \
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl bootstrap gui/$(id -u) "$PLIST_FILE" 2>/dev/null || \
        launchctl load "$PLIST_FILE" 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} macOS 开机自启动已配置（后台运行，无终端窗口）"
    echo -e "    管理命令:"
    echo -e "      停止:  ${CYAN}launchctl unload $PLIST_FILE${NC}"
    echo -e "      重启:  ${CYAN}launchctl unload $PLIST_FILE && launchctl load $PLIST_FILE${NC}"
    echo -e "      查看日志: ${CYAN}tail -f $AGENT_HOME/logs/launchd-stdout.log${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# 配置 Linux 开机自启动（systemd user unit）
# ─────────────────────────────────────────────────────────────────────────────
elif [[ "$(uname -s)" == "Linux" ]] && [ "$WANT_AUTOSTART" = "1" ]; then
    UNIT_DIR="$HOME/.config/systemd/user"
    UNIT_FILE="$UNIT_DIR/agentbase.service"
    mkdir -p "$UNIT_DIR"

    if [ ! -f "$UNIT_FILE" ]; then
        cat > "$UNIT_FILE" << UNIT
[Unit]
Description=AgentBase
After=network.target

[Service]
Type=simple
ExecStart=$HOME/.local/bin/agentbase --no-browser
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
UNIT
        systemctl --user daemon-reload
        systemctl --user enable agentbase.service
        systemctl --user start agentbase.service
        echo -e "  ${GREEN}✓${NC} Linux 开机自启动已配置（systemd user unit）"
    else
        echo -e "  ${GREEN}✓${NC} Linux 开机自启动已配置"
    fi
fi
echo ""
