# packaging/win/build_exe.spec — PyInstaller spec for ShortcutViewer.exe (Windows, onefile).
# Windows에서 실행:  packaging\win\build_exe.bat   (또는  pyinstaller --clean packaging/win/build_exe.spec)
import os

HERE = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.dirname(os.path.dirname(HERE))   # packaging/win → packaging → repo 루트

def d(relpath):   # (source, dest-in-bundle) — bundle_root()/relpath 로 그대로 복원되게 폴더 구조 유지
    return (os.path.join(ROOT, relpath), os.path.dirname(relpath) or ".")

datas = [
    d("win/build_win.py"), d("win/winkeys.py"),
    d("render.py"), d("svkeys.py"), d("svann.py"), d("viewer.template.html"),
    d("dump_ae.py"), d("dump_premiere.py"), d("dump_photoshop.py"), d("dump_illustrator.py"),
]
# win/defaults·win/packs(공유 corpus)는 있으면 통째로 포함 — 없어도(첫 빌드) 정상 진행
for sub in ("win/defaults", "win/packs"):
    p = os.path.join(ROOT, sub)
    if os.path.isdir(p):
        datas.append((p, sub))

a = Analysis(
    [os.path.join(HERE, "launcher.py")],
    pathex=[],
    binaries=[],
    datas=datas,
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
    name="ShortcutViewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # 콘솔 유지 — 첫 실행 진단용 로그가 보여야 함(v1). 안정화되면 False로 바꿀 수 있음.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
