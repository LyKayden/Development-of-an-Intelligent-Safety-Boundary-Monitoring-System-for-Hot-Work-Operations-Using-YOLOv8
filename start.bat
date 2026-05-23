@echo off
chcp 65001 >nul
title Hotwork Monitoring System - Starter

:: ============================================================
:: 获取脚本所在目录（相对路径，去掉尾部反斜杠）
:: ============================================================
set PROJECT_DIR=%~dp0
set PROJECT_DIR=%PROJECT_DIR:~0,-1%

echo ============================================================
echo          Hotwork Monitoring System - Start
echo ============================================================
echo.
echo  Project Directory: %PROJECT_DIR%
echo.

:: ============================================================
:: 自动检测 conda 安装位置
:: ============================================================
set CONDA_PATH=

if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=C:\ProgramData\miniconda3\Scripts\conda.exe
    goto conda_found
)

if exist "C:\Users\%USERNAME%\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=C:\Users\%USERNAME%\miniconda3\Scripts\conda.exe
    goto conda_found
)

if exist "%LOCALAPPDATA%\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=%LOCALAPPDATA%\miniconda3\Scripts\conda.exe
    goto conda_found
)

if exist "F:\Tools\Miniconda3\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=F:\Tools\Miniconda3\miniconda3\Scripts\conda.exe
    goto conda_found
)

where conda >nul 2>nul
if %errorlevel% equ 0 (
    set CONDA_PATH=conda
    goto conda_found
)

echo [ERROR] Conda not found
pause
exit /b 1

:conda_found
echo [OK] Conda found: %CONDA_PATH%

:: 获取 conda 根目录
for /f "delims=" %%i in ('%CONDA_PATH% info --base 2^>nul') do set CONDA_ROOT=%%i
echo [OK] Conda root: %CONDA_ROOT%
echo.

:: ============================================================
:: 检查 yolov8 环境
:: ============================================================
if not exist "%CONDA_ROOT%\envs\yolov8\python.exe" (
    echo [ERROR] yolov8 environment not found
    pause
    exit /b 1
)
set YOLOV8_PYTHON=%CONDA_ROOT%\envs\yolov8\python.exe
echo [OK] yolov8 environment found

:: ============================================================
:: 检查项目文件
:: ============================================================
if not exist "%PROJECT_DIR%\backend\app.py" (
    echo [ERROR] backend\app.py not found
    pause
    exit /b 1
)
echo [OK] backend\app.py exists

:: 修改：检查前端是否已打包（生产模式）
if exist "%PROJECT_DIR%\frontend\dist\index.html" (
    echo [OK] Frontend already built (dist/index.html exists)
) else (
    echo [WARNING] Frontend not built, building now...

    :: 检查 Node.js
    where node >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Node.js not found, required for building frontend
        pause
        exit /b 1
    )
    echo [OK] Node.js found

    :: 执行打包
    cd /d %PROJECT_DIR%\frontend
    call npm run build
    if %errorlevel% neq 0 (
        echo [ERROR] Frontend build failed
        pause
        exit /b 1
    )
    echo [OK] Frontend build completed
    cd /d %PROJECT_DIR%
)

if exist "%PROJECT_DIR%\models\best.pt" (
    echo [OK] models\best.pt exists
) else (
    echo [WARNING] models\best.pt not found
)
echo.

:: ============================================================
:: 检查 Python 依赖
:: ============================================================
"%YOLOV8_PYTHON%" -c "import flask" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python dependencies not installed
    echo Please run install.bat
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

:: ============================================================
:: 启动服务（生产模式：只启动 Flask）
:: ============================================================
echo.
echo ============================================================
echo Starting system...
echo ============================================================
echo.

echo [1/2] Starting backend service (Flask + Frontend)...
start "Backend Service" cmd /k "cd /d %PROJECT_DIR%\backend && %YOLOV8_PYTHON% app.py"
timeout /t 5 >nul

echo [2/2] Opening browser...
:: 修改：端口改为 5000
start http://localhost:5000/

echo.
echo ============================================================
echo          System started successfully!
echo ============================================================
echo.
echo Instructions:
echo 1. Do not close the command window (Backend Service)
echo 2. Browser will open the monitoring interface (Port 5000)
echo 3. To stop, close the window or double-click stop.bat
echo.
echo Production Mode: Frontend is served by Flask (No Node.js needed)
echo.

:: start.bat 自动关闭（不暂停）
timeout /t 2 >nul
exit /b 0
