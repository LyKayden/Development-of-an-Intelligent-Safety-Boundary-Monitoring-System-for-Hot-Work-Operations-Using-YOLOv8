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

:: ========== 检查 Node.js ==========
:: 保留：打包时需要 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 Node.js
    echo 请先安装 Node.js: https://nodejs.org/zh-cn/
    echo 安装后重启此脚本
    pause
    exit /b 1
)
echo ✓ Node.js 已安装
echo.

:: ========== 检查 conda ==========
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

:: ========== 检查项目文件 ==========
if not exist "%PROJECT_DIR%\backend\requirements.txt" (
    echo ❌ 错误：找不到 backend\requirements.txt
    echo 请确认项目文件完整
    pause
    exit /b 1
)
echo ✓ backend\requirements.txt 存在

if not exist "%PROJECT_DIR%\frontend\package.json" (
    echo ❌ 错误：找不到 frontend\package.json
    echo 请确认项目文件完整
    pause
    exit /b 1
)
echo ✓ frontend\package.json 存在
echo.

:: ========== [1/4] 检查/创建 conda 环境 ==========
echo ============================================================
echo [1/4] 检查 conda 环境 (yolov8)...
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

:: ========== [2/4] 检查/安装 Python 依赖 ==========
echo ============================================================
echo [2/4] 检查 Python 依赖...
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

:: ========== [3/4] 检查/安装前端依赖 ==========
echo ============================================================
echo [3/4] 检查前端依赖...
echo ============================================================

:: 检查 node_modules 文件夹是否存在
if exist "%PROJECT_DIR%\frontend\node_modules" (
    echo ✓ 前端依赖已安装 (node_modules 存在)，跳过安装
    goto npm_done
) else (
    echo ⚠️  前端依赖未安装，正在安装...
    cd /d %PROJECT_DIR%\frontend
    call npm install
    if %errorlevel% neq 0 (
        echo ❌ 前端依赖安装失败
        pause
        exit /b 1
    )
    echo ✓ 前端依赖安装成功
)

:npm_done
echo.

:: ========== [4/4] 检查模型文件 ==========
echo ============================================================
echo [4/4] 检查模型文件...
echo ============================================================
:: 修改：模型文件改为 best.pt
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
:: 修改：端口改为 5000
echo  1. 双击 start.bat 启动系统
echo  2. 浏览器自动打开 http://localhost:5000/
echo.
echo  📁 卸载命令：
echo  %CONDA_PATH% env remove -n yolov8
echo.
echo ============================================================
pause
