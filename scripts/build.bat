@echo off
title Build OpenKoreUtils.exe
cd /d "%~dp0\.."

echo Installing PyInstaller if needed...
py -3 -m pip install --quiet pyinstaller

echo.
echo Building (openkore_utils module)...
py -3 -m PyInstaller --noconfirm --onefile --windowed --uac-admin --name "OpenKoreUtils" ^
  --paths "src" ^
  --distpath "%~dp0\.." ^
  --workpath "%~dp0\..\build\pyinstaller" ^
  --specpath "%~dp0\..\build\pyinstaller" ^
  --collect-submodules openkore_utils ^
  src\openkore_utils\__main__.py

if exist "%~dp0\..\OpenKoreUtils.exe" (
    echo.
    echo [OK] Created: %~dp0\..\OpenKoreUtils.exe
) else (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

pause
