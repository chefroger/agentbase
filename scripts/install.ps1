# ==============================================================================
# AgentBase — 一键安装脚本 (Windows PowerShell)
# ==============================================================================
# 使用方式:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# 全程使用 venv，不碰系统 Python site-packages。
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  AgentBase — 安装向导" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: 检查 Python
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "Step 1/5: 检查 Python 环境" -ForegroundColor White

# AgentBase 必须跑在 **Python 3.14** 上：Hermes 从 v0.21.6 起只提供 3.14 的依赖集
# （requires-python 里那个 `>=3.11` 只是留给旧安装「跑完自己的升级步骤」的过渡桥），
# 而 AgentBase 是**进程内**嵌 Hermes 的，解释器必须与 Hermes 的托管环境同 ABI。
# 在 3.11~3.13 上会变成「装得上、起不来」，所以这里不再接受 3.11~3.13。
$PythonCmd = $null

# 判据：解释器正好是 3.14（不是「>= 3.11」下限）
$IsPython314 = { param($cmd) & $cmd -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)" 2>$null; $LASTEXITCODE -eq 0 }

foreach ($cmd in @("python3.14", "python3", "python")) {
    try {
        if (& $IsPython314 $cmd) {
            $PythonCmd = $cmd
            Write-Host "  ✓ Python 3.14 ($(& $PythonCmd -c "import sys; print(sys.executable)"))" -ForegroundColor Green
            break
        }
    } catch {}
}

# 退路：Hermes 自带的托管解释器 —— 优先用它：与 Hermes 的运行时 ABI 完全一致。
#
# **刻意不写死布局**。2026-10-15 用户实测（Linux 侧同源问题）：按代码推断出来的单一
# glob 在真机上一个都匹配不到 —— 真实布局有两棵代际树，且代际里还套一层 venv/
# （权威来源 pm/operations.py:152/210 `generation / "venv"`、
#   pm/install_states.py:72 的两棵树）。写死布局一旦猜错就是「静默找不到」。
# 所以改成**递归找 + 按版本号验**：对布局变化免疫，多找到的由 $IsPython314 兜住
# （任一份 3.14 都能建 AgentBase 的 venv，同为 cp314 ABI）。
# -Depth 6 刚好到 <tree>\<gen>\venv\Scripts\python.exe，再深就进 Lib\site-packages 了。
if (-not $PythonCmd) {
    $candidates = Get-ChildItem -Path "$HermesHome\installs", "$HermesHome\tools" `
        -Filter "python*.exe" -Recurse -Depth 6 -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^python(3\.14)?\.exe$' }
    foreach ($cand in $candidates) {
        try {
            if (& $IsPython314 $cand.FullName) {
                $PythonCmd = $cand.FullName
                Write-Host "  ✓ 使用 Hermes 自带的 Python 3.14 ($PythonCmd)" -ForegroundColor Green
                break
            }
        } catch {}
    }
}

if (-not $PythonCmd) {
    Write-Host "  ✗ 需要 Python 3.14，但未找到。" -ForegroundColor Red
    Write-Host ""
    Write-Host "  AgentBase 需要 Python 3.14（内置 Hermes 也运行在同一解释器上）。" -ForegroundColor White
    Write-Host "  安装一个 3.14 后重新运行本脚本：" -ForegroundColor White
    Write-Host "       winget install Python.Python.3.14"
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# 创建 venv
# ─────────────────────────────────────────────────────────────────────────────
$AgentHome = if ($env:AGENT_HOME) { $env:AGENT_HOME } else { "$env:LOCALAPPDATA\agentbase" }
$VenvReal = "$AgentHome\venv"
$VenvDir  = $VenvReal
# 非空 = 旧环境还在原地、新环境建在 .new 里、依赖装完才切换（切换点见 Step 3 末尾）
$VenvOld  = $null

# 已有 venv 但解释器**不是 3.14** → 必须重建。旧装机器就地升级 agentbase 时，代码与依赖
# 都换了、venv 的解释器还是旧的（`agentbase update` 只更新代码与依赖，不重建 venv），
# 于是 Hermes 的 pm 激活会把 cp314 的包塞进旧解释器 → 聊天只报「AI Agent 模块未加载」。
# **重建不会丢任何用户数据**：数据在 $AgentHome 下（数据库、公司目录），不在 venv 里。
if ((Test-Path "$VenvDir\Scripts\python.exe") -and -not (& $IsPython314 "$VenvDir\Scripts\python.exe")) {
    Write-Host "  ! 已有的运行环境不是 Python 3.14 —— 正在重建（不会动你的数据）..." -ForegroundColor Yellow
    # 换掉之前留一份已装包清单：venv 里可能有用户手动 pip install 的东西，
    # 这份清单是事后唯一的追查线索。失败不影响安装（best-effort）。
    try {
        if (-not (Test-Path $AgentHome)) { New-Item -ItemType Directory -Path $AgentHome -Force | Out-Null }
        & "$VenvDir\Scripts\pip.exe" freeze 2>$null | Out-File -FilePath "$AgentHome\venv-packages-before-rebuild.txt" -Encoding utf8
        Write-Host "  → 已把重建前的包清单留档：$AgentHome\venv-packages-before-rebuild.txt" -ForegroundColor Cyan
    } catch {}
    # **不在原地重建**（2026-10-16 改，与 install.sh 同步）。原实现是 Remove-Item 后立刻重建，
    # 中间任何一步失败（断网 / 磁盘满 / 找不到 3.14 / 依赖装不上）都会留下
    # 「旧的已经删了、新的没建成」——用户软件直接打不开，而客群是电脑小白，无力自救。
    # 改为把新环境建到 .new、依赖全部装成功后才切换，失败时旧环境原样可用。
    $VenvOld = $VenvDir
    $VenvDir = "$VenvReal.new"
    # 只清上一次失败残留的 .new —— 它从来不是用户数据，删了不影响任何人
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
}
if (-not (Test-Path "$VenvDir\Scripts\python.exe")) {
    Write-Host "  → 创建虚拟环境..."
    & $PythonCmd -m venv $VenvDir
}
$PipCmd = "$VenvDir\Scripts\pip.exe"
$PyCmd  = "$VenvDir\Scripts\python.exe"
Write-Host "  ✓ 虚拟环境就绪 ($VenvDir)" -ForegroundColor Green

# 克隆或更新一个 git 仓库；失败返回 $false，由调用方决定是否中止。
#
# 为什么要这些判断（与 install.sh 同步，都是实测踩出来的）：
#   1. 只有目录**是有效 git 仓库**（.git 且 HEAD 可解析）才算「已安装」。克隆被中断时
#      git 会留下空目录，旧逻辑 Test-Path 会把它当成已装 → 之后 pull 静默失败、
#      pip 在残缺树里报出误导性错误，且**重试永远无法恢复**。
#   2. 浅克隆 --depth 1：全历史克隆在弱网下最慢、最易失败。跟 main 时本地没有 tag，
#      Hermes 版本推导会退化为「未知」（AgentBase 警告后继续启动）；固定版本模式
#      （--branch <tag>）会把该 tag 一并带上，版本可正常解出。
#   3. 不吞 git 的 stderr：用户要靠它排查网络问题。
function Invoke-CloneOrUpdate {
    param([string]$Name, [string]$Repo, [string]$Dest, [string]$Ref = "main")

    $isRepo = $false
    if (Test-Path "$Dest\.git") {
        git -C $Dest rev-parse --verify HEAD 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $isRepo = $true }
    }

    if ($isRepo) {
        # 固定版本模式（Ref != main，Hermes 用）：不 pull —— 在 tag 检出上 pull main
        # 会把它拖到 main 尖端，固定就失去意义。已有检出保持原样。
        if ($Ref -ne "main") {
            Write-Host "  → 已有 $Name 检出，保持现状（固定版本 $Ref，不跟随 main）" -ForegroundColor Cyan
            return $true
        }
        Write-Host "  → 更新已有仓库..." -ForegroundColor Cyan
        git -C $Dest pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠ git pull 失败，继续使用现有代码" -ForegroundColor Yellow
        }
        return $true
    }

    if (Test-Path $Dest) {
        Write-Host "  ⚠ 已存在的目录不是有效的代码仓库（上次克隆中断的残留），重新克隆：$Dest" -ForegroundColor Yellow
        Remove-Item -Recurse -Force $Dest
    }

    New-Item -ItemType Directory -Path (Split-Path $Dest -Parent) -Force | Out-Null
    git clone --depth 1 --branch $Ref $Repo $Dest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ 无法克隆 $Name（git 的报错见上）。请确认网络后重新运行本脚本。" -ForegroundColor Red
        return $false
    }
    return $true
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Hermes（内置）
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Step 2/5: Hermes（内置）" -ForegroundColor White

# 任务书 v2 §10.7：Hermes 源码随框架分发在 vendor/hermes/，用户不需要单独安装。
# 真正的完整性检查在 Step 3（clone 之后）—— 这一步仓库还没落地。
# 隔离铁律：HERMES_HOME 固定指向 AGENT_HOME（%LOCALAPPDATA%\agentbase），
# vendored Hermes 永不读写用户自己的 %LOCALAPPDATA%\hermes。
Write-Host "  OK Hermes 随 agentbase 内置分发，无需单独安装" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: 安装 agentbase
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Step 3/5: 安装 AgentBase" -ForegroundColor White

$AgentbaseRepo = "https://github.com/chefroger/agentbase.git"
$AgentbaseDir = "$AgentHome\agentbase"

# 记录回滚点（2026-10-16 加，与 install.sh 同步）。重建场景下依赖若装不上，代码必须能
# 退回升级前 —— 否则「新代码 + 旧 venv」照样起不来，等于把「重建失败」升级成「彻底打不开」。
# 新装用户这里是空的，Invoke-RollbackCode 自然什么都不做。
$AgentbaseHeadBefore = $null
if (Test-Path "$AgentbaseDir\.git") {
    $sha = git -C $AgentbaseDir rev-parse HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and $sha) { $AgentbaseHeadBefore = "$sha".Trim() }
}

function Invoke-RollbackCode {
    if (-not $AgentbaseHeadBefore) { return }
    Write-Host "  ⚠ 正在把代码回退到升级前的版本（$($AgentbaseHeadBefore.Substring(0,8))）..." -ForegroundColor Yellow
    git -C $AgentbaseDir reset --hard $AgentbaseHeadBefore 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ 代码已回退，旧版本仍可正常使用" -ForegroundColor Green
    } else {
        Write-Host "  ✗ 代码回退失败 —— 请把上面的输出发给技术支持" -ForegroundColor Red
    }
    # 丢弃半成品的新环境；旧环境（$VenvOld）始终没被动过
    if ($VenvOld -and (Test-Path $VenvDir)) { Remove-Item -Recurse -Force $VenvDir }
}

if (-not (Invoke-CloneOrUpdate "agentbase" $AgentbaseRepo $AgentbaseDir)) { exit 1 }

Push-Location $AgentbaseDir

# ── 内置 Hermes 完整性检查（clone 到这里之后才能查）──────────────────────
if (Test-Path "$AgentbaseDir\vendor\hermes\hermes_cli") {
    $VendorVer = if (Test-Path "$AgentbaseDir\vendor\hermes\VERSION") {
        (Get-Content "$AgentbaseDir\vendor\hermes\VERSION" -Raw).Trim()
    } else { "unknown" }
    Write-Host "  OK 内置 Hermes $VendorVer（vendor/hermes，已接管不再跟踪上游）" -ForegroundColor Green
} else {
    Write-Host "  ✗ 仓库缺少内置 Hermes：vendor\hermes\hermes_cli" -ForegroundColor Red
    Write-Host "    仓库不完整，请重新下载/克隆 agentbase。" -ForegroundColor White
    Pop-Location
    exit 1
}

# 装依赖：框架自身 + Hermes 的依赖闭包（vendor 源码不 pip 安装，但依赖要装）。
# 每个 pip 后都必须查 $LASTEXITCODE —— 原生命令非零退出不抛异常（见本文件前面的说明），
# 不查就会在弱网/磁盘满时把失败当成成功，用户之后运行 agentbase 只得到
# ModuleNotFoundError，且开机自启任务每次登录静默失败。
& $PipCmd install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ 依赖安装失败（pip 的报错见上）。请检查网络后重新运行本脚本。" -ForegroundColor Red
    Invoke-RollbackCode
    Pop-Location
    exit 1
}
& $PipCmd install -r requirements-hermes.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Hermes 依赖安装失败（pip 的报错见上）。" -ForegroundColor Red
    Invoke-RollbackCode
    Pop-Location
    exit 1
}
& $PipCmd install -e "." --no-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ AgentBase 安装失败（pip 的报错见上）。" -ForegroundColor Red
    Invoke-RollbackCode
    Pop-Location
    exit 1
}

# 可选依赖：客户语义检索用的向量扩展（sqlite-vec）。
# **单独装、失败只警告** —— 不是主链依赖：不装则语义检索自动降级关键词，
# 其余功能零影响；个别平台（如 Windows ARM）没有对应 wheel，
# 不能因为一个可选能力让整台机器的安装失败。
& $PyCmd -c "import sqlite_vec" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ sqlite-vec 已安装（客户语义检索可用）" -ForegroundColor Green
} else {
    & $PipCmd install "sqlite-vec>=0.1.6" *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ sqlite-vec 安装完成（客户语义检索可用）" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ sqlite-vec 未安装：客户语义检索将降级为关键词检索（其余功能不受影响）" -ForegroundColor Yellow
    }
}
Pop-Location

# 真实探针：确认装完确实能导入（与 Step 2 的 `import hermes_cli` 对齐）。
# 只看 pip 退出码还不够 —— editable 安装可能"成功"但路径不对。
& $PyCmd -c "import agentbase.app"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ AgentBase 装好了但无法导入，安装不完整。" -ForegroundColor Red
    Invoke-RollbackCode
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# 新运行环境验证通过后，才切换到位（对应前面的 .new 方案）
#
# 为什么压到这么后面：切换是**唯一不可逆的一步**。把它放在「建 venv / git pull /
# pip install / import 探针」全部成功之后，失败面就只剩两个目录改名 —— 本地文件
# 操作，几乎不会失败；即便失败，下面也保留了 .old 供恢复。
# ─────────────────────────────────────────────────────────────────────────────
if ($VenvOld) {
    Write-Host "  → 新运行环境已就绪，正在切换..." -ForegroundColor Cyan
    $VenvOldBak = "$VenvOld.old"
    if (Test-Path $VenvOldBak) { Remove-Item -Recurse -Force $VenvOldBak }
    $swapOk = $false
    try {
        Move-Item -Path $VenvOld -Destination $VenvOldBak -Force
        Move-Item -Path $VenvDir -Destination $VenvOld -Force
        $swapOk = $true
    } catch {}
    if ($swapOk) {
        if (Test-Path $VenvOldBak) { Remove-Item -Recurse -Force $VenvOldBak }
        $VenvDir = $VenvOld
        $PipCmd  = "$VenvDir\Scripts\pip.exe"
        $PyCmd   = "$VenvDir\Scripts\python.exe"
        Write-Host "  ✓ 已切换到 Python 3.14 运行环境" -ForegroundColor Green
    } else {
        # 把旧环境挪回来，丢弃半成品
        Write-Host "  ✗ 切换运行环境失败，正在恢复原环境..." -ForegroundColor Red
        if (Test-Path $VenvOldBak) { Move-Item -Path $VenvOldBak -Destination $VenvOld -Force }
        if (Test-Path "$VenvReal.new") { Remove-Item -Recurse -Force "$VenvReal.new" }
        Invoke-RollbackCode
        exit 1
    }
}

Write-Host "  ✓ AgentBase 安装完成" -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: 安装内置 skills
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Step 4/5: 安装内置 skills" -ForegroundColor White

# 必须用真实存在的入口：此前写的是 `python -m agentbase.post_install install`，而该包
# **没有 __main__.py** → 从未生效过；再加上原生命令失败不抛异常，旧代码会在失败时
# 照样打印「✓ 完成」（虚假成功）。实测新装后 skills 数为 0。
& $PyCmd -c "from agentbase.post_install import install_skills; install_skills()"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 内置 skills 安装完成" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 内置 skills 安装可能不完整（首次启动时会自动同步）" -ForegroundColor Yellow
}

# chat-memory 插件：agentbase 自带的工具（让 LLM 能查 conversations 表的历史对话）。
# setup() 会兜底同步 + 写 config.yaml；这里做一次显式的初始安装，幂等。
& $PyCmd -c "from agentbase.bootstrap import sync_chat_memory_plugin, ensure_chat_memory_plugin_enabled; sync_chat_memory_plugin(); ensure_chat_memory_plugin_enabled()"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ chat-memory 插件已部署到 $AgentHome\plugins\chat-memory" -ForegroundColor Green
} else {
    Write-Host "  ⚠ chat-memory 插件部署失败（首次启动时会自动重试）" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: 初始化数据目录
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Step 5/5: 初始化数据目录" -ForegroundColor White

$DataDir = "$AgentHome\data"
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
New-Item -ItemType Directory -Path "$AgentHome\workspaces" -Force | Out-Null

try {
    & $PyCmd -c "from agentbase.database import init_db; init_db()" 2>$null
    Write-Host "  ✓ 数据库初始化完成 ($DataDir\agentbase.db)" -ForegroundColor Green
} catch {
    Write-Host "  → 数据库将在首次启动时自动初始化" -ForegroundColor Cyan
}

# ─────────────────────────────────────────────────────────────────────────────
# 导出 agentbase 命令
# ─────────────────────────────────────────────────────────────────────────────
$LocalBin = "$env:LOCALAPPDATA\local\bin"
New-Item -ItemType Directory -Path $LocalBin -Force | Out-Null

@"
@echo off
set HERMES_HOME=$AgentHome
REM 禁用 Hermes 懒加载重启：否则 agent 创建时会被 exec 到 Hermes 自带的 store python
REM （那里没有 agentbase 包），agent 线程以 RelaunchExit(SystemExit) 静默死亡，
REM 前端只会看到「Agent 未返回有效响应」。bootstrap.py 里也设了一处，这里是双保险。
set HERMES_DISABLE_LAZY_INSTALLS=1
"$PyCmd" "$AgentbaseDir\server.py" %*
"@ | Out-File -FilePath "$LocalBin\agentbase.cmd" -Encoding OEM

# 检测 PATH 中是否已包含 $LocalBin
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$LocalBin*") {
    [Environment]::SetEnvironmentVariable("PATH", "$LocalBin;$currentPath", "User")
    Write-Host "  ✓ 已将 agentbase 命令加入 PATH（新终端生效）" -ForegroundColor Green
}

# ─────────────────────────────────────────────────────────────────────────────
# 开机自启动（隐藏窗口）+ 桌面快捷方式
#
# 委托给 agentbase.post_install.win_setup —— 那是唯一实现，服务启动时也会幂等调用。
# 以前这里用 Register-ScheduledTask 直接跑 python.exe，是控制台程序 → 登录必弹
# 终端窗口；而且只在这一处配，走「让 Hermes 装 AgentBase」流程的用户根本拿不到。
# ─────────────────────────────────────────────────────────────────────────────
# 重新安装 = 恢复默认：清掉「用户手动关闭自启」的偏好记录
& $PyCmd -c "from agentbase.service import reset_autostart_preference; reset_autostart_preference()"
& $PyCmd -c "from agentbase.post_install.win_setup import ensure_windows_setup, agentbase_dir_from_module; [print('  ' + m) for m in ensure_windows_setup(agentbase_dir_from_module())]"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ 开机自启动/桌面快捷方式设置失败（不影响 AgentBase 使用，可稍后重试）" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────────────────────────────
# 安装后自检（快检：零 token，不发真实请求）
#
# 端到端验活（真发一次对话 / 一张图 / 一次搜索）在**首次启动时**跑 ——
# 那时服务与配置都已就位，且结果会落盘、在界面提示。这里只做能立刻发现
# "装坏了"的快检，避免安装脚本因为网络波动误报失败而挡住用户。
# ─────────────────────────────────────────────────────────────────────────────
# 两处都必须在调 doctor 之前处理：
#   1. `prepare_hermes_import_paths()` —— Hermes 不再装进 AgentBase 的 venv，不先准备
#      sys.path 就直接 import doctor 会报 `No module named 'run_agent'`（干净机器实测）。
#   2. doctor 自己会 import Hermes，会触发 pm 激活剥离 venv 的 site-packages；
#      那一步的恢复也在这个函数里，漏了会让后面 holehe/sqlite-vec 误报「未安装」。
# 「Hermes 版本」这一项刻意不计入致命项：版本过旧不需要在这里解决 —— AgentBase 启动后
# 会在界面里自动升级 Hermes（见 agentbase/hermes_upgrade.py）。若这里判失败并退出，
# 用户就永远看不到那个升级界面了。
& $PyCmd -c "import sys; from agentbase.bootstrap import prepare_hermes_import_paths; prepare_hermes_import_paths(); from agentbase.doctor import run_doctor, format_report, has_fatal_failure; r = run_doctor(deep=False); print(format_report(r)); sys.exit(1 if has_fatal_failure(r, ignore_names=('Hermes 版本',)) else 0)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ 自检发现致命问题，安装不完整。请把上面的输出发给技术支持。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "══ 安装完成 ══" -ForegroundColor Green
Write-Host ""
Write-Host "  启动方式:"
Write-Host "    新终端: agentbase"
Write-Host "    或: $PyCmd $AgentbaseDir\server.py"
Write-Host "    AgentBase 将在每次开机后自动启动（后台静默运行）"
Write-Host ""
Write-Host "  启动后打开: http://127.0.0.1:9120/agentbase"
Write-Host ""
Write-Host "  数据位置:"
Write-Host "    用户数据: $AgentHome\"
Write-Host "    Hermes 配置: $HermesHome\"
Write-Host ""
