# -*- mode: python ; coding: utf-8 -*-
import os

# This file is a configuration script for PyInstaller. It tells PyInstaller
# how to process your application and what files to include.

# -----------------------------------------------------------------------------
# -- DATA FILES CONFIGURATION
# -----------------------------------------------------------------------------
# The 'datas' list tells PyInstaller which additional files and directories
# to bundle with your application. The format for each entry is a tuple:
#   ('source_path_on_disk', 'destination_path_in_bundle')
#
# For directories, PyInstaller copies the entire contents. The build script
# (build.py) ensures these source directories exist and are not empty.
datas = [
    ('data', 'data'),
    ('src/icons', 'src/icons'),
    ('templates', 'templates'),
    ('src/style.qss', 'src'),
]

# -----------------------------------------------------------------------------
# -- HIDDEN IMPORTS
# -----------------------------------------------------------------------------
# List of modules that PyInstaller's static analysis might miss. This is
# common for libraries that use dynamic imports or plugins.
hiddenimports = [
    'PySide6.QtXml',
    'PySide6.QtSvg',
    'qt_material',  # For the application theme
]

# -----------------------------------------------------------------------------
# -- EXCLUDED MODULES
# -----------------------------------------------------------------------------
# List of modules to explicitly exclude from the build. This is useful for
# resolving conflicts between libraries, such as the one between PySide6 and PyQt6.
excludes = [
    'PyQt6',
    'PyQt6-sip',
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

# -----------------------------------------------------------------------------
# -- MAIN ANALYSIS
# -----------------------------------------------------------------------------
# This is where PyInstaller analyzes your main script ('main.py') to find
# all required Python modules and libraries.
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# -----------------------------------------------------------------------------
# -- BUNDLE CREATION
# -----------------------------------------------------------------------------
# This section defines the final executable and its properties.

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Encoding Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False = GUI application (no command window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/icons/logo.png' if os.path.exists('src/icons/logo.png') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Encoding Manager',
) 