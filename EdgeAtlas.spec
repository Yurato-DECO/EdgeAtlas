# Build with: .venv\Scripts\python.exe -m PyInstaller --noconfirm EdgeAtlas.spec
from pathlib import Path

root = Path(SPECPATH)
data_files = [(str(root / name), name if (root / name).is_dir() else '.')
              for name in ('assets', 'vendor', 'map.html', 'icon.png', 'README.md')]

a = Analysis(
    [str(root / 'app.py')],
    pathex=[str(root)],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pytest', 'PySide6.QtTest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='EdgeAtlas', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    disable_windowed_traceback=False,
    icon=str(root / 'icon.png'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='EdgeAtlas')
