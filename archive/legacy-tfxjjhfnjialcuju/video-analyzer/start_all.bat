@echo off
chcp 65001 > nul
echo ============================================================
echo  Video Content Analyzer - 一键启动所有服务
echo ============================================================

set SCRIPT_DIR=C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer
set PYTHON_EXE=C:\Program Files\QClaw\v0.2.32.610\resources\python\python.exe

REM 检查 Python 是否可用
"%PYTHON_EXE%" --version > nul 2>&1
if errorlevel 1 (
    echo [错误] Python 不可用: %PYTHON_EXE%
    pause
    exit /b 1
)

echo.
echo [1/3] 检查端口占用...
netstat -ano | findstr ":8765.*LISTENING" > nul 2>&1
if not errorlevel 1 (
    echo   ⚠️  端口 8765 已被占用（页面服务可能已在运行）
) else (
    echo   ✅ 端口 8765 可用
)

netstat -ano | findstr ":8766.*LISTENING" > nul 2>&1
if not errorlevel 1 (
    echo   ⚠️  端口 8766 已被占用（转写服务可能已在运行）
) else (
    echo   ✅ 端口 8766 可用
)

echo.
echo [2/3] 启动页面服务（端口 8765）...
start "PageService" cmd /k "cd /d %SCRIPT_DIR% && \"%PYTHON_EXE%\" simple_server.py"
timeout /t 2 > nul

echo.
echo [3/3] 启动转写服务（端口 8766, tiny 模型）...
start "TranscribeService" cmd /k "cd /d %SCRIPT_DIR% && \"%PYTHON_EXE%\" transcribe_server.py --model tiny"
timeout /t 5 > nul

echo.
echo ============================================================
echo  所有服务已启动！
echo ============================================================
echo.
echo  页面服务  http://127.0.0.1:8765/web_player_v3.html
echo  转写服务  http://127.0.0.1:8766/
echo.
echo  局域网访问（替换 IP 为你的局域网 IP）:
echo  http://192.168.0.8:8765/web_player_v3.html
echo.
echo  服务窗口已打开，关闭窗口即可停止服务
echo.
pause
