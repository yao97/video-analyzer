"""
一键修复转写服务：杀卡死进程 → 重启 → 测试
"""
import subprocess
import os
import time
import socket

PORT = 8766
SCRIPT_DIR = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer"

def kill_port(port):
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}',
                              shell=True, capture_output=True, text=True)
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    print(f"[1/4] 杀掉端口 {port} 的进程 PID={pid}")
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True,
                                 capture_output=True)
                    time.sleep(2)
                    return True
        print(f"[1/4] 端口 {port} 未被占用")
        return False
    except Exception as e:
        print(f"[1/4] 杀端口失败: {e}")
        return False

def start_service():
    print(f"[2/4] 启动转写服务（small 模型）...")
    cmd = f'start "TranscribeService" cmd /k "cd /d {SCRIPT_DIR} && python transcribe_server.py"'
    subprocess.Popen(cmd, shell=True)
    print("  服务窗口已打开，等待模型加载...")
    return True

def wait_for_port(port, timeout=120):
    print(f"[3/4] 等待服务就绪（最多 {timeout} 秒）...")
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
        time.sleep(3)
        print("  still waiting...")
    return False

def test_api():
    print("[4/4] 测试 API...")
    try:
        import requests
        resp = requests.get(f'http://127.0.0.1:{PORT}/api/video-meta', timeout=10)
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            print("  ✅ API 正常响应")
            return True
        else:
            print(f"  ⚠️ API 返回异常: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ API 测试失败: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("转写服务一键修复")
    print("=" * 60)

    # Step 1: Kill old process
    kill_port(PORT)
    time.sleep(1)

    # Step 2: Start new service
    start_service()

    # Step 3: Wait for port ready
    if wait_for_port(PORT, timeout=120):
        print("  ✅ 端口 8766 已就绪")
    else:
        print("  ❌ 服务启动超时（120 秒）")
        print("  请检查服务窗口是否有报错")
        exit(1)

    # Step 4: Test API
    time.sleep(2)
    if test_api():
        print("\n" + "=" * 60)
        print("✅ 转写服务修复成功！")
        print("=" * 60)
        print(f"\n服务地址: <ADDRESS_REMOVED>
        print("请在浏览器中刷新页面，重新上传视频测试。")
    else:
        print("\n" + "=" * 60)
        print("❌ API 测试失败")
        print("=" * 60)
        print("请检查服务窗口日志，或尝试用 tiny 模型（更快）：")
        print("  python transcribe_server.py --model tiny")
