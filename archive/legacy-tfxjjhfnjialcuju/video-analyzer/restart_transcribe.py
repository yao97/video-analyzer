"""
重启转写服务 + 测试
"""
import subprocess
import os
import time
import socket

PORT = 8766
SCRIPT_DIR = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer"

def kill_port(port):
    """杀掉占用端口的进程"""
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}',
                              shell=True, capture_output=True, text=True)
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    print(f"杀掉端口 {port} 的进程 PID={pid}")
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True,
                                 capture_output=True)
                    time.sleep(1)
    except Exception as e:
        print(f"杀端口失败: {e}")

def wait_for_port(port, timeout=120):  # 延长到 120 秒，small 模型加载慢
    """等待端口就绪"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(2)
    return False

# 1. 杀掉旧进程
print("=" * 60)
print("重启转写服务")
print("=" * 60)
print("\n[1/3] 清理旧进程...")
kill_port(PORT)
time.sleep(2)

# 2. 启动新服务
print("\n[2/3] 启动转写服务（small 模型，首次加载约 30-60 秒）...")
cmd = f'start "TranscribeService" cmd /k "python transcribe_server.py"'
proc = subprocess.Popen(cmd, shell=True, cwd=SCRIPT_DIR)
print("  服务窗口已打开，正在加载模型...")

# 3. 等待服务就绪
print("\n[3/3] 等待服务就绪...")
if wait_for_port(PORT, timeout=120):
    print("  ✅ 端口 8766 已就绪")
    print("\n" + "=" * 60)
    print("服务启动成功！")
    print("=" * 60)
    print("\n转写服务地址: <ADDRESS_REMOVED>
    print("请在浏览器中刷新页面，重新上传视频测试。")
else:
    print("  ❌ 服务启动超时（120 秒）")
    print("\n可能原因：")
    print("  1. small 模型首次下载（~244MB，需等待）")
    print("  2. 端口 8766 被其他程序占用")
    print("  3. Python 依赖缺失（whisper / imageio-ffmpeg / flask）")
    print("\n请检查服务窗口的错误信息。")
