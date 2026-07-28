# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH)
soundcard_datas, soundcard_binaries, soundcard_hidden = collect_all("soundcard")

if sys.platform == "darwin":
    executable_icon = str(project_root / "assets" / "raucous.icns")
elif sys.platform.startswith("win"):
    executable_icon = str(project_root / "assets" / "raucous.ico")
else:
    executable_icon = None

a = Analysis(
    [str(project_root / "src" / "raucous" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=soundcard_binaries,
    datas=soundcard_datas
    + [(str(project_root / "src" / "raucous" / "assets" / "icon.png"), "raucous/assets")],
    hiddenimports=soundcard_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Raucous",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=sys.platform == "darwin",
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=executable_icon,
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Raucous",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collection,
        name="Raucous.app",
        icon=str(project_root / "assets" / "raucous.icns"),
        bundle_identifier="dev.anubhavgupta.raucous",
        info_plist={
            "CFBundleDisplayName": "Raucous",
            "CFBundleShortVersionString": "1.2.0",
            "CFBundleVersion": "1.2.0",
            "NSMicrophoneUsageDescription": (
                "Raucous uses an audio input or virtual loopback device only "
                "to animate the local visualizer. Audio is never saved or uploaded."
            ),
            "LSMinimumSystemVersion": "12.0",
        },
    )
