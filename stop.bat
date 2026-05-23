@echo off
title 动火作业智能监控系统 - 停止器

echo ============================================================
echo          🔥 动火作业智能监控系统 - 停止
echo ============================================================
echo.

:: 修改：只终止 Python 进程（生产模式没有 Node 前端服务）
taskkill /F /FI "WINDOWTITLE eq Backend Service*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *app.py*" 2>nul

:: 修改：移除 Node 进程终止（生产模式不需要）
:: taskkill /F /FI "WINDOWTITLE eq Frontend Service*" 2>nul

echo ✅ 系统已停止
echo.
pause
