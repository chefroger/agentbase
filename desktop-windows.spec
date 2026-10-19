# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the AgentBase Windows single-file executable.

Phase 7 方案 A：AgentBase.exe 只跑后端，双击后打开系统浏览器。

- console=False：双击不弹终端窗口（常驻服务由自启的 VBS 隐藏启动）。
- 单文件：EXE 直接携带 binaries/datas（不生成 COLLECT 目录）。
- vendor/hermes 以源码目录（datas）随包分发，见 bootstrap._adjust_sys_path()。
"""
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
        (str(_PROJECT_ROOT / 'agentbase'), 'agentbase'),
        (str(_PROJECT_ROOT / 'static'), 'static'),
        (str(_PROJECT_ROOT / 'pyproject.toml'), '.'),
        (str(_PROJECT_ROOT / 'docs'), 'docs'),
        (str(_PROJECT_ROOT / 'CHANGELOG.md'), '.'),
        (str(_PROJECT_ROOT / 'vendor' / 'hermes'), 'vendor/hermes'),
    ],
    hiddenimports=[
        'uvicorn.loops.auto', 'uvicorn.protocols.http.auto',
        'agentbase', 'agentbase.api', 'agentbase.api.chat', 'agentbase.api.cron',
        'agentbase.api.workspaces', 'agentbase.api.conversations', 'agentbase.api.memory',
        'agentbase.api.onboarding', 'agentbase.api.license', 'agentbase.api.deps',
        'agentbase.api.settings', 'agentbase.api.packs', 'agentbase.api.files',
        'agentbase.api.branding',
        'agentbase.api.business_config', 'agentbase.api.meta',
        'agentbase.database', 'agentbase.workspace', 'agentbase.workspace.crud',
        'agentbase.workspace.workdir',
        'agentbase.helpers', 'agentbase.prompts', 'agentbase.prompt',
        'agentbase.skill_router', 'agentbase.skill_registry', 'agentbase.skill_semantic',
        'agentbase.chat_memory', 'agentbase.memory', 'agentbase.license',
        'agentbase.onboarding', 'agentbase.bootstrap', 'agentbase.cli',
        'agentbase.service', 'agentbase.opener', 'agentbase.pdf_vision',
        'agentbase.usage_directions', 'agentbase.paths', 'agentbase.process',
        'agentbase.updater', 'agentbase.updater.state', 'agentbase.updater.engine',
        'agentbase.updater.sources', 'agentbase.updater.changelog',
        'agentbase.post_install', 'agentbase.post_install.skills',
        'agentbase.post_install.win_setup',
        'openai', 'anthropic',
        'pymupdf', 'fitz', 'anydoc', 'pypdfium2',
        'psutil', 'dns',
        'asyncio', 'sqlite3', 'json', 'csv', 'io', 're', 'hashlib', 'filecmp',
        'multiprocessing',
        # Hermes 的运行时依赖：Hermes 以源码 datas 分发，PyInstaller 不会静态分析，
        # 必须在 hiddenimports 里显式列出（否则 frozen 启动时才报 ModuleNotFoundError）。
        'certifi', 'truststore', 'dotenv', 'fire', 'httpx', 'socksio',
        'rich', 'tenacity', 'tomli_w', 'ruamel.yaml', 'requests', 'jinja2',
        'prompt_toolkit', 'croniter', 'snowballstemmer', 'markdown', 'jwt',
        'urllib3', 'cryptography', 'websockets', 'browser_harness', 'pathspec',
        'httptools', 'watchfiles', 'multipart', 'PIL', 'pillow_heif', 'resvg_py',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',
              'PySide6', 'PyQt5', 'PyQt6', 'webview',
              'PyInstaller', 'pytest'],
    cipher=_block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    [],
    name='AgentBase',
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
