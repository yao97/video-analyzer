@echo off
rem ============================================================
rem  Video Content Analyzer - 单一真相源启动脚本
rem  唯一真相源：C:\Users\EDY\Projects\video-analyzer
rem  后端 8766 一并托管前端（Flask FRONTEND_DIR=../frontend）
rem  启动后访问：  http://192.168.0.8:8766/
rem  旧 .qclaw 部署（8765/8766）已废弃，请勿再运行其 start_services.bat
rem ============================================================
rem ── 路径均从本脚本所在目录推导，避免硬编码漂移 ──
set ROOT=%~dp0
set VENV=%ROOT%backend\venv\Scripts
set BACKEND=%ROOT%backend

start "" "%VENV%\pythonw.exe" "%BACKEND%\transcribe_server.py" --host 0.0.0.0 --port 8766
exit /b 0
