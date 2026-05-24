# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parents[1]

a = Analysis(
    [str(ROOT / "src" / "helper.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "dashboard"), "dashboard"),
        (str(ROOT / "prompts"), "prompts"),
        *collect_data_files("browser_use", includes=["agent/system_prompts/*.md"]),
    ],
    hiddenimports=[
        *collect_submodules("browser_use.agent.system_prompts"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        "recordings",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="flyingpig-helper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
