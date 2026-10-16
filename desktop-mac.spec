# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TradeWin macOS .app bundle (pywebview)."""
from pathlib import Path

_block_cipher = None
_PROJECT_ROOT = Path(SPECPATH)

a = Analysis(
    [str(_PROJECT_ROOT / 'desktop.py')],
    pathex=[str(_PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(_PROJECT_ROOT / 'skills'), 'skills'),
        (str(_PROJECT_ROOT / '.agentbase-template'), '.agentbase-template'),
        (str(_PROJECT_ROOT / 'trade'), 'trade'),
        (str(_PROJECT_ROOT / 'static'), 'static'),
        (str(_PROJECT_ROOT / 'pyproject.toml'), '.'),
    ],
    hiddenimports=[
        'uvicorn.loops.auto', 'uvicorn.protocols.http.auto',
        'trade', 'agentbase.api', 'agentbase.api.chat', 'agentbase.api.cron',
        'agentbase.api.companies', 'agentbase.api.customers', 'agentbase.api.libraries',
        'agentbase.api.orders', 'agentbase.api.conversations', 'agentbase.api.memory',
        'agentbase.api.onboarding', 'agentbase.api.license', 'agentbase.api.deps',
        'agentbase.database', 'agentbase.company', 'agentbase.company.crud', 'agentbase.company.workdir',
        'agentbase.helpers', 'agentbase.prompts', 'agentbase.prompt',
        'agentbase.skill_router', 'agentbase.skill_registry',
        'agentbase.chat_memory', 'agentbase.memory', 'agentbase.license',
        'agentbase.onboarding', 'agentbase.bootstrap',
        'agentbase.osint', 'agentbase.osint.orchestrator', 'agentbase.osint.whois',
        'agentbase.osint.email_verify', 'agentbase.osint.sanctions', 'agentbase.osint.sanctions.loader',
        'agentbase.osint.tech_stack', 'agentbase.osint.linkedin_verify',
        'agentbase.osint.scoring', 'agentbase.osint.constants',
        'hermes_cli', 'hermes_cli.config', 'hermes_cli.auth',
        'hermes_cli.env_loader', 'hermes_cli.models',
        'hermes_constants', 'run_agent',
        'openai', 'anthropic',  # LLM Provider SDKs — required, not optional
        'pymupdf', 'anydoc', 'pypdfium2',  # 文档解析 / 图纸渲染（扫描件走 vision）
        'psutil', 'dnspython',  # Process management / DNS lookups
        'webview', 'webview.platforms.cocoa',
        'asyncio', 'sqlite3', 'json', 'csv', 'io', 're', 'hashlib',
        'multiprocessing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL',
              'PySide6', 'PyQt5', 'PyQt6'],
    cipher=_block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    [],
    name='TradeWin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='TradeWin.app',
    icon=None,
    bundle_identifier='ai.smarttrade.desktop',
    info_plist={
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
        'NSSupportsAutomaticTermination': True,
    },
)
