# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Foreign Trade Assistant standalone app
#
# Build:
#   pip install pyinstaller
#   pyinstaller pyinstaller.spec
#
# Output: dist/Foreign Trade Assistant.app (macOS) / dist/ (Windows)

import sys
from pathlib import Path

_block_cipher = None

# project root
ROOT = Path(SPECPATH)  # SPECPATH = directory where this .spec file lives

# files to bundle with the app
_static_files = [
    (str(ROOT / "static" / "app.html"), "static"),
]
_skill_files = []
_skills_dir = ROOT / "skills"
if _skills_dir.is_dir():
    for _skill_d in _skills_dir.iterdir():
        if _skill_d.is_dir() and _skill_d.name.startswith("b2b-"):
            _skill_md = _skill_d / "SKILL.md"
            if _skill_md.is_file():
                _skill_files.append((str(_skill_md), f"skills/{_skill_d.name}"))
# also add chat-memory skill
_chat_skill = _skills_dir / "chat-memory" / "SKILL.md"
if _chat_skill.is_file():
    _skill_files.append((str(_chat_skill), "skills/chat-memory"))

_template_files = []
_template_dir = ROOT / ".agentbase-template"
if _template_dir.is_dir():
    for _f in _template_dir.rglob("*"):
        if _f.is_file():
            _dest = str(_f.relative_to(ROOT))
            _template_files.append((str(_f), str(_f.parent.relative_to(ROOT))))

# hidden imports that PyInstaller may miss
_hidden_imports = [
    "agentbase", "agentbase.api", "agentbase.api.companies", "agentbase.api.onboarding",
    "agentbase.api.libraries", "agentbase.api.customers", "agentbase.api.conversations",
    "agentbase.api.chat", "agentbase.api.memory", "agentbase.api.deps",
    "agentbase.osint", "agentbase.osint.constants", "agentbase.osint.whois",
    "agentbase.osint.email_verify", "agentbase.osint.sanctions",
    "agentbase.osint.tech_stack", "agentbase.osint.linkedin_verify",
    "agentbase.osint.scoring", "agentbase.osint.orchestrator",
    "agentbase.database", "agentbase.company", "agentbase.library",
    "agentbase.customer", "agentbase.chat_memory", "agentbase.memory",
    "agentbase.helpers", "agentbase.prompt", "agentbase.prompts",
    "agentbase.skill_router", "agentbase.skill_registry",
    "agentbase.onboarding", "agentbase.email_intel", "agentbase.post_install",
    "hermes_cli", "hermes_cli.config", "hermes_cli.auth",
    "hermes_cli.env_loader", "hermes_cli.models",
    "hermes_constants", "run_agent",
    "openai", "anthropic",  # LLM Provider SDKs — required, not optional
    "pymupdf", "anydoc", "pypdfium2",  # 文档解析 / 图纸渲染（扫描件走 vision）
    "psutil", "dnspython",  # Process management / DNS lookups
    "fastapi", "uvicorn", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "starlette", "pydantic", "anyio", "yaml",
]

a = Analysis(
    [str(ROOT / "server.py")],
    pathex=[str(ROOT), str(ROOT / "agentbase")],
    binaries=[],
    datas=_static_files + _skill_files + _template_files,
    hiddenimports=_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "pandas", "numpy", "scipy",
        "PIL", "cv2", "tensorflow", "torch", "sklearn",
        "jedi", "ipython", "jupyter", "notebook",
        "pytest", "coverage", "flake8",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=_block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Foreign Trade Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "static" / "icon.icns") if (ROOT / "static" / "icon.icns").is_file() else None,
)

app = BUNDLE(
    exe,
    name="Foreign Trade Assistant.app",
    icon=str(ROOT / "static" / "icon.icns") if (ROOT / "static" / "icon.icns").is_file() else None,
    bundle_identifier="com.foreign-agentbase.assistant",
    info_plist={
        "NSHighResolutionCapable": True,
        "CFBundleShortVersionString": "0.3.0",
        "CFBundleName": "Foreign Trade Assistant",
        "LSBackgroundOnly": False,
        "NSSupportsAutomaticGraphicsSwitching": True,
    },
)
