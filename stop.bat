@echo off
chcp 65001 >nul
title 动火作业智能监控系统 - 停止器

echo ============================================================
echo          🔥 动火作业智能监控系统 - 停止
echo ============================================================
echo.

:: 方法：通过查找占用 5000 端口的进程并强制结束（最准确）
echo 正在停止后端服务 (Port 5000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>nul
)

:: 备用方法：尝试通过窗口标题关闭（防止端口法漏掉）
taskkill /F /FI "WINDOWTITLE eq Backend Service" >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq Hotwork Monitoring System - Starter" >nul 2>nul

echo ✅ 系统已停止
echo.
pause
