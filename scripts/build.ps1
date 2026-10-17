# ==============================================================================
# AgentBase — Windows Build Script (Phase 7)
# ==============================================================================
# 使用 PyInstaller 打包为单文件 AgentBase.exe（无控制台窗口）。
#
# 前置要求（在项目的 venv 中执行）：
#   pip install pyinstaller
#   pip install -e .
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1
# ==============================================================================

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=============================" -ForegroundColor White
Write-Host "  AgentBase — Build (Windows)" -ForegroundColor White
Write-Host "=============================" -ForegroundColor White

if (-not (python -c "import PyInstaller" 2>$null)) {
    Write-Host "→ 安装 PyInstaller..." -ForegroundColor Cyan
    python -m pip install pyinstaller
}

Write-Host "→ 清理旧构建..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item -Force *.spec.bak -ErrorAction SilentlyContinue

Write-Host "→ 开始打包（单文件，约需数分钟）..." -ForegroundColor Cyan
python -m PyInstaller desktop-windows.spec --noconfirm --clean

$Exe = Join-Path $Root "dist\AgentBase.exe"
if (Test-Path $Exe) {
    $Size = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "构建完成" -ForegroundColor Green
    Write-Host "  位置: $Exe" -ForegroundColor Green
    Write-Host "  大小: $Size MB" -ForegroundColor Green
} else {
    Write-Host "✗ 构建失败，请检查上方错误信息" -ForegroundColor Red
    exit 1
}
