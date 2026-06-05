@echo off
chcp 65001 >nul
title 动火作业智能监控系统 - 安装器

:: 获取脚本所在目录（相对路径）
set PROJECT_DIR=%~dp0
:: (去掉尾部反斜杠)
set PROJECT_DIR=%PROJECT_DIR:~0,-1%

echo ============================================================
echo          🔥 动火作业智能监控系统 - 一键安装
echo ============================================================
echo.
echo  📁 项目目录：%PROJECT_DIR%
echo.

:: ========== 检查 conda (后端运行必需) ==========
if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=C:\ProgramData\miniconda3\Scripts\conda.exe
    goto conda_found
)
if exist "C:\Users\%USERNAME%\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=C:\Users\%USERNAME%\miniconda3\Scripts\conda.exe
    goto conda_found
)
if exist "F:\Tools\Miniconda3\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=F:\Tools\Miniconda3\miniconda3\Scripts\conda.exe
    goto conda_found
)
if exist "%LOCALAPPDATA%\miniconda3\Scripts\conda.exe" (
    set CONDA_PATH=%LOCALAPPDATA%\miniconda3\Scripts\conda.exe
    goto conda_found
)

echo ❌ 错误：未检测到 Miniconda/Anaconda
echo 请先安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html
pause
exit /b 1

:conda_found
echo ✓ conda 已安装：%CONDA_PATH%

:: 获取 conda 根目录
for /f "delims=" %%i in ('%CONDA_PATH% info --base') do set CONDA_ROOT=%%i
echo ✓ conda 根目录：%CONDA_ROOT%
echo.

:: ========== 检查后端项目文件 ==========
if not exist "%PROJECT_DIR%\backend\requirements.txt" (
    echo ❌ 错误：找不到 backend\requirements.txt
    echo 请确认项目文件完整
    pause
    exit /b 1
)
echo ✓ backend\requirements.txt 存在
echo.

:: ========== [1/3] 检查/创建 conda 环境 ==========
echo ============================================================
echo [1/3] 检查 conda 环境 (yolov8)...
echo ============================================================

:: 检查 yolov8 环境文件夹是否存在
if exist "%CONDA_ROOT%\envs\yolov8\python.exe" (
    echo ✓ yolov8 环境已存在，跳过创建
    goto env_exists
) else (
    echo ⚠️  yolov8 环境不存在，正在创建...
    call %CONDA_PATH% create -n yolov8 python=3.13 -y
    if %errorlevel% neq 0 (
        echo ❌ conda 环境创建失败
        pause
        exit /b 1
    )
    echo ✓ conda 环境创建成功
)

:env_exists
echo.

:: ========== [2/3] 检查/安装 Python 依赖 ==========
echo ============================================================
echo [2/3] 检查 Python 依赖...
echo ============================================================

:: 使用 yolov8 环境的 python.exe 检查 flask 是否已安装
"%CONDA_ROOT%\envs\yolov8\python.exe" -c "import flask" >nul 2>nul
if %errorlevel% equ 0 (
    echo ✓ Python 依赖已安装，跳过安装
    goto python_deps_done
) else (
    echo ⚠️  Python 依赖未安装，正在安装...
    call %CONDA_PATH% activate yolov8
    cd /d %PROJECT_DIR%\backend
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Python 依赖安装失败
        pause
        exit /b 1
    )
    echo ✓ Python 依赖安装成功
)

:python_deps_done
echo.

:: ========== [3/3] 检查前端预打包文件 (核心修改) ==========
echo ============================================================
echo [3/3] 检查前端预打包文件 (dist)...
echo ============================================================

if exist "%PROJECT_DIR%\frontend\dist\index.html" (
    echo ✓ 发现预打包的前端文件 (dist/index.html)
    echo 💡 提示：普通用户无需安装 Node.js 即可运行！
    echo    (仅当您需要修改 Vue 源码时，才需安装 Node.js 并运行 npm install)
    goto frontend_done
) else (
    echo ⚠️  警告：未找到 frontend\dist\index.html
    echo    如果您只是运行系统，请确保下载了完整的预打包版本。
    echo    如果您是开发者，请安装 Node.js 并运行 npm run build。
    echo.
)

:frontend_done
echo.

:: ========== 检查模型文件 ==========
echo ============================================================
echo 🔍 检查模型文件...
echo ============================================================
if exist "%PROJECT_DIR%\models\best.pt" (
    echo ✓ 模型文件已存在 (best.pt)
) else (
    echo ⚠️  模型文件不存在 (models/best.pt)
    echo 请先训练模型并保存为 PyTorch 格式
    echo 或联系开发者获取模型文件
)
echo.

:: ========== 完成 ==========
echo ============================================================
echo          ✅ 安装完成！
echo ============================================================
echo.
echo  📌 下一步：
echo  1. 双击 start.bat 启动系统
echo  2. 浏览器自动打开 http://localhost:5000/
echo.
echo  📁 卸载命令：
echo  %CONDA_PATH% env remove -n yolov8
echo.
echo ============================================================
pause
