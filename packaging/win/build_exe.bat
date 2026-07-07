@echo off
REM packaging\win\build_exe.bat — Windows에서 실행: ShortcutViewer.exe 생성 (PyInstaller, onefile).
REM 사용법: 이 저장소를 Windows에 clone한 뒤, repo 루트에서:  packaging\win\build_exe.bat
setlocal
cd /d "%~dp0..\.."

where python >nul 2>&1 || (echo Python이 필요합니다 — https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요. & exit /b 1)

python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
  echo PyInstaller 설치 중…
  python -m pip install --user pyinstaller || exit /b 1
)

echo.
echo 빌드 중… (몇 분 걸릴 수 있습니다)
python -m PyInstaller --clean --noconfirm --distpath packaging\win\dist --workpath packaging\win\build packaging\win\build_exe.spec
if errorlevel 1 exit /b 1

echo.
echo 완료: packaging\win\dist\ShortcutViewer.exe
echo 배포 전 체크: 서명 없음 -^> SmartScreen "Windows의 PC 보호" 경고가 뜨면 "추가 정보" -^> "실행"으로 넘기면 됩니다.
endlocal
