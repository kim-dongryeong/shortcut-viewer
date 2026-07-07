#!/usr/bin/env python3
# packaging/win/launcher.py — PyInstaller가 이 파일을 통째로 얼려 ShortcutViewer.exe로 만든다.
# 번들된 스크립트/코퍼스를 %LOCALAPPDATA%\ShortcutViewer\ (영구 쓰기 가능 위치)로 복사한 뒤
# 그 자리에서 win/build_win.py → render.py를 원래 스크립트 그대로 실행하고 viewer.html을 연다.
#
# PyInstaller onefile은 매 실행마다 임시 폴더(sys._MEIPASS)에 압축을 풀고 종료 시 지운다 — 거기다
# 바로 shortcuts.json/viewer.html을 쓰면 브라우저가 열기도 전에 파일이 사라질 위험이 있어서,
# 실행할 스크립트들을 영구 위치로 복사해 그 자리에서 돌린다(사용자가 직접 clone해서 돌리는 것과 동일 구조).
import os, sys, shutil, runpy, webbrowser, traceback

def bundle_root():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def run_script(path):
    old_argv = sys.argv
    try:
        sys.argv = [os.path.basename(path)]   # 각 스크립트 자체 인자 파싱과 안 섞이게 초기화
        runpy.run_path(path, run_name="__main__")
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        sys.argv = old_argv

def main():
    src = bundle_root()
    dst = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "ShortcutViewer")
    os.makedirs(dst, exist_ok=True)
    # 사용자 데이터(스캔 결과·개인 설정)는 덮어쓰지 않고, 스크립트/코퍼스만 매번 최신으로 갱신
    keep = shutil.ignore_patterns("shortcuts.json", "viewer.html", "annotations.json",
                                   "manual_globals_win.json", "vscode_default_keybindings.json")
    for name in ("win", "render.py", "svkeys.py", "svann.py", "viewer.template.html",
                 "dump_ae.py", "dump_premiere.py", "dump_photoshop.py", "dump_illustrator.py"):
        s = os.path.join(src, name)
        if not os.path.exists(s):
            continue
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True, ignore=keep)
        else:
            shutil.copy2(s, d)

    os.chdir(dst)
    print("▸ 단축키 수집 중… (win/build_win.py)")
    run_script(os.path.join(dst, "win", "build_win.py"))
    print("▸ 뷰어 렌더링 중… (render.py)")
    run_script(os.path.join(dst, "render.py"))

    viewer = os.path.join(dst, "viewer.html")
    if os.path.exists(viewer):
        webbrowser.open("file:///" + viewer.replace(os.sep, "/"))
    else:
        print("\n문제가 발생했습니다 — 위 로그를 확인해 주세요.")
        input("(Enter를 누르면 창이 닫힙니다)")

if __name__ == "__main__":
    main()
