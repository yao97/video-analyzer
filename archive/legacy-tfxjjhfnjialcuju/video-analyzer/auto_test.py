"""
自动化测试脚本 - Video Analyzer
一键启动服务 + 测试所有功能 + 生成报告
"""
import os
import sys
import time
import socket
import subprocess
import json
from pathlib import Path

# 配置
ANALYZER_DIR = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer"
PORT_PAGE = 8765
PORT_TRANSCRIBE = 8766
TEST_VIDEO = r"C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4"
LAN_IP = "192.168.0.8"

def log(msg, level='INFO'):
    """打印日志（无 emoji，兼容 GBK）"""
    prefix = {
        'INFO': '[INFO]',
        'OK': '[PASS]',
        'FAIL': '[FAIL]',
        'WARN': '[WARN]',
    }.get(level, '[INFO]')
    print(f"{prefix} {msg}")
    sys.stdout.flush()  # Force flush

def kill_port(port):
    """杀掉占用端口的进程"""
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}',
                              shell=True, capture_output=True, text=True)
        if result.stdout:
            lines = [l for l in result.stdout.strip().split('\n') if 'LISTENING' in l]
            for line in lines:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    log(f"Killing process on port {port} (PID={pid})", 'WARN')
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True,
                                 capture_output=True)
                    time.sleep(0.5)
            return True
    except Exception as e:
        log(f"Failed to kill port {port}: {e}", 'FAIL')
    return False

def wait_for_port(port, host='127.0.0.1', timeout=30):
    """等待端口就绪"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(1)
    return False

def start_service(script_name, port, cwd):
    """启动服务（新窗口）"""
    cmd = f'start "VideoAnalyzer-{port}" cmd /k "python \"{script_name}\""'
    log(f"Starting service: {script_name} (port {port})")
    # 用 subprocess 启动（不等待）
    subprocess.Popen(cmd, shell=True, cwd=cwd)
    # 等待服务就绪
    log(f"Waiting for port {port}...", 'INFO')
    if wait_for_port(port, timeout=30):
        log(f"Port {port} is ready", 'OK')
        return True
    else:
        log(f"Port {port} startup timeout", 'FAIL')
        return False

def test_endpoint(url, method='GET', data=None, files=None):
    """测试 HTTP 端点"""
    try:
        import requests
        if method == 'GET':
            resp = requests.get(url, timeout=5)
        elif method == 'POST':
            resp = requests.post(url, data=data, files=files, timeout=10)
        return resp.status_code, resp.text[:500]
    except Exception as e:
        return None, str(e)

def main():
    log("=" * 60, 'INFO')
    log("Video Analyzer Automated Test", 'INFO')
    log("=" * 60, 'INFO')
    
    # 1. 杀掉旧进程
    log("[1/6] Cleaning up old processes...", 'INFO')
    kill_port(PORT_PAGE)
    kill_port(PORT_TRANSCRIBE)
    time.sleep(2)
    
    # 2. 启动页面服务
    log("[2/6] Starting page service...", 'INFO')
    if not start_service('simple_server.py', PORT_PAGE, ANALYZER_DIR):
        log("Page service failed to start, exiting", 'FAIL')
        return
    
    # 3. 启动转写服务
    log("[3/6] Starting transcription service...", 'INFO')
    log("(First load of small model may take 30 seconds)", 'WARN')
    if not start_service('transcribe_server.py', PORT_TRANSCRIBE, ANALYZER_DIR):
        log("Transcription service failed to start, exiting", 'FAIL')
        return
    
    # 4. 测试页面服务
    log("[4/6] Testing page service...", 'INFO')
    urls_to_test = [
        f"http://127.0.0.1:{PORT_PAGE}/web_player_v3.html",
        f"http://{LAN_IP}:{PORT_PAGE}/web_player_v3.html",
    ]
    for url in urls_to_test:
        status, text = test_endpoint(url)
        if status == 200:
            log(f"[PASS] {url} - Status {status}", 'OK')
        else:
            log(f"[FAIL] {url} - {status or 'No response'}", 'FAIL')
    
    # 5. 测试转写服务 API
    log("[5/6] Testing transcription API...", 'INFO')
    api_urls = [
        f"http://127.0.0.1:{PORT_TRANSCRIBE}/api/video-meta",
    ]
    for url in api_urls:
        status, text = test_endpoint(url)
        if status in [200, 404, 405]:  # 405 = Method Not Allowed (OK)
            log(f"[PASS] {url} - Status {status}", 'OK')
        else:
            log(f"[FAIL] {url} - {status or 'No response'}", 'FAIL')
    
    # 6. 测试视频上传 + 转写（如果有测试视频）
    log("[6/6] Testing video upload + transcription...", 'INFO')
    if os.path.exists(TEST_VIDEO):
        log(f"Test video: {TEST_VIDEO}", 'INFO')
        # 上传视频
        upload_url = f"http://127.0.0.1:{PORT_TRANSCRIBE}/api/transcribe"
        try:
            import requests
            with open(TEST_VIDEO, 'rb') as f:
                files = {'video': (os.path.basename(TEST_VIDEO), f, 'video/mp4')}
                data = {'duration': '45'}
                resp = requests.post(upload_url, files=files, data=data, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    job_id = result.get('job_id')
                    log(f"[PASS] Upload successful, job_id={job_id}", 'OK')
                    # 轮询状态
                    log("Polling transcription status...", 'INFO')
                    for i in range(120):  # 最多等 120 秒（small 模型较慢）
                        time.sleep(1)
                        status_url = f"http://127.0.0.1:{PORT_TRANSCRIBE}/api/status/{job_id}"
                        s, t = test_endpoint(status_url)
                        if s == 200:
                            status_data = json.loads(t)
                            status = status_data.get('status')
                            progress = status_data.get('progress', 0)
                            log(f"  Status: {status}, Progress: {progress}%")
                            if status == 'done':
                                log("[PASS] Transcription complete!", 'OK')
                                # 获取结果
                                result_url = f"http://127.0.0.1:{PORT_TRANSCRIBE}/api/result/{job_id}"
                                s2, t2 = test_endpoint(result_url)
                                if s2 == 200:
                                    result_data = json.loads(t2)
                                    segments = result_data.get('result', {}).get('segments', [])
                                    log(f"[PASS] Recognized {len(segments)} segments", 'OK')
                                break
                            elif status == 'error':
                                log(f"[FAIL] Transcription failed: {status_data.get('error')}", 'FAIL')
                                break
                    else:
                        log("[FAIL] Transcription timeout (120s)", 'FAIL')
                else:
                    log(f"[FAIL] Upload failed: {resp.status_code}", 'FAIL')
        except Exception as e:
            log(f"[FAIL] Test failed: {e}", 'FAIL')
    else:
        log(f"[WARN] Test video not found: {TEST_VIDEO}", 'WARN')
        log("Skipping upload test", 'WARN')
    
    # 总结
    log("=" * 60, 'INFO')
    log("Test complete", 'INFO')
    log("=" * 60, 'INFO')
    log(f"\nLocal access: http://127.0.0.1:{PORT_PAGE}/web_player_v3.html")
    log(f"LAN access: http://{LAN_IP}:{PORT_PAGE}/web_player_v3.html")
    log("\nServices are running in separate windows. Close them manually when done.")
    log("Press Enter to exit this script...")
    input()

if __name__ == '__main__':
    main()
