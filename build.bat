@echo off
:: ─────────────────────────────────────────────────────────────────────────
:: SmartBack - PyInstaller Build Script
:: Run this script from the project root directory.
:: Output: dist\SmartBack.exe
:: ─────────────────────────────────────────────────────────────────────────

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   SmartBack v1.0 - Build Script      ║
echo  ╚══════════════════════════════════════╝
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)

:: Install / upgrade dependencies
echo  [1/3] Installing dependencies...
pip install -r requirements.txt --quiet
pip install -r requirements-dev.txt --quiet

:: Clean previous build artifacts
echo  [2/3] Cleaning previous build...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist SmartBack.spec del /f SmartBack.spec

:: Build the EXE
echo  [3/3] Building SmartBack.exe ...
echo.

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name SmartBack ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=win32gui ^
    --hidden-import=win32process ^
    --hidden-import=pywintypes ^
    --hidden-import=psutil ^
    --hidden-import=keyboard ^
    smart_back.py

:: Check result
if exist "dist\SmartBack.exe" (
    echo.
    echo  ╔══════════════════════════════════════════════════════╗
    echo  ║   BUILD SUCCESSFUL                                    ║
    echo  ║   Output: dist\SmartBack.exe                         ║
    echo  ║                                                       ║
    echo  ║   Next step: Run setup_startup.ps1 as Administrator  ║
    echo  ║   to add SmartBack to Windows startup.               ║
    echo  ╚══════════════════════════════════════════════════════╝
) else (
    echo.
    echo  [ERROR] Build failed. Check the output above for details.
)

echo.
pause
