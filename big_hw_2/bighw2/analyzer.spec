# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for the Rust-like language analyzer."""

import os
from pathlib import Path

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = Path(SPEC_DIR).parent  # big_hw_2/
BIGHW2_DIR = Path(SPEC_DIR)           # bighw2/
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

a = Analysis(
    [str(BIGHW2_DIR / "server.py")],
    pathex=[str(BIGHW2_DIR)],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), "frontend_dist"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RustAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # keep console so user sees the URL + can Ctrl+C
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
