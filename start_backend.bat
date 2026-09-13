@echo off
REM 启动 Video Analyzer 转写后端（修复版，单一真相源：Projects/video-analyzer/backend）
REM 双击本文件即可在独立命令行窗口常驻运行；关闭窗口即停止服务。
REM 如 8766 端口被占用，先结束占用该端口的旧 python 进程再双击。
set ROOT=%~dp0
cd /d "%ROOT%backend"
"%ROOT%backend\venv\Scripts\python.exe" transcribe_server.py --host 0.0.0.0 --port 8766
echo.
echo 服务已停止。按任意键关闭窗口...
pause >nul
