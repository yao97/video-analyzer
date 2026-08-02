"""
一键诊断 + 修复语音转写问题
"""
import subprocess, os, socket, time, json, sys, re

PORT = 8766
SCRIPT_DIR = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer"
PYTHON = r"C:\Program Files\QClaw\v0.2.31.600\resources\python\python.exe"

def log(msg, level="INFO"):
    tag = {"INFO":"📌", "OK":"✅", "FAIL":"❌", "WARN":"⚠️"}[level]
    print(f"  {tag} {msg}")

def kill_old():
    print("\n[1/6] 杀掉旧进程...")
    r = subprocess.run(f'netstat -ano | findstr :{PORT}', shell=True, capture_output=True, text=True)
    pids = set()
    for line in r.stdout.strip().split('\n'):
        if 'LISTENING' in line:
            pids.add(line.strip().split()[-1])
    for pid in pids:
        log(f"杀掉 PID={pid}", "WARN")
        subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True)
    time.sleep(2)
    log("完成", "OK")

def start_service():
    print("\n[2/6] 启动转写服务 (tiny 模型)...")
    cmd = f'start "WhisperService" cmd /k "cd /d {SCRIPT_DIR} && "{PYTHON}" transcribe_server.py --model tiny"'
    subprocess.Popen(cmd, shell=True)
    # 等待启动
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            if s.connect_ex(('127.0.0.1', PORT)) == 0:
                s.close()
                log(f"服务已启动 (端口 {PORT})", "OK")
                return True
            s.close()
        except:
            pass
        time.sleep(3)
    log("启动超时（60秒）", "FAIL")
    return False

def test_api():
    print("\n[3/6] 测试 API 端点...")
    import requests
    try:
        r = requests.get(f'http://127.0.0.1:{PORT}/api/video-meta', timeout=10)
        if r.status_code == 200:
            log(f"GET /api/video-meta → 200 {r.json()}", "OK")
        else:
            log(f"GET /api/video-meta → {r.status_code}", "FAIL")
            return False
    except Exception as e:
        log(f"API 无响应: {e}", "FAIL")
        return False
    return True

def check_frontend():
    print("\n[4/6] 检查前端 JS...")
    path = os.path.join(SCRIPT_DIR, 'web_player_v3.html')
    with open(path, encoding='utf-8') as f:
        content = f.read()
    issues = []
    # 检查 TRANSCRIBE_BASE 定义
    if 'TRANSCRIBE_BASE' not in content:
        issues.append("TRANSCRIBE_BASE 未定义")
    else:
        log("TRANSCRIBE_BASE 已定义", "OK")
    # 检查 fetch 调用格式
    broken = re.findall(r'fetch\(\$ \{[^`]*\)', content)
    if broken:
        issues.append(f"发现 {len(broken)} 处 fetch 语法错误")
    else:
        log("fetch() 调用语法正确", "OK")
    # 检查 processFile 是否调用 startTranscription
    if 'startTranscription(file' not in content and 'startTranscription(file,' not in content:
        issues.append("processFile 中未找到 startTranscription 调用")
    else:
        log("processFile → startTranscription 调用链路正常", "OK")
    if issues:
        for i in issues:
            log(i, "FAIL")
        return False
    return True

def fix_frontend():
    print("\n[5/6] 修复前端 JS（添加错误日志）...")
    path = os.path.join(SCRIPT_DIR, 'web_player_v3.html')
    with open(path, encoding='utf-8') as f:
        content = f.read()
    modified = False
    # 在 startTranscription 函数开头添加日志
    if 'console.log(\'[Transcribe] 开始上传' not in content:
        old = 'async function startTranscription(file, duration) {'
        new = '''async function startTranscription(file, duration) {
  console.log('[Transcribe] 开始上传', file?.name, 'duration:', duration);'''
        if old in content:
            content = content.replace(old, new, 1)
            modified = True
            log("添加 startTranscription 入口日志", "OK")
    # 在 catch 块中添加更详细的错误日志
    if 'console.error(\'[Transcribe] 上传失败' not in content:
        old = '    console.error(\'Transcribe start failed:\', e);\n    return null;'
        new = '''    console.error('[Transcribe] 上传失败:', e);
    toast('转写服务连接失败，请确认服务已启动（端口 8766）', 'error');
    return null;'''
        if old in content:
            content = content.replace(old, new, 1)
            modified = True
            log("添加转写失败 toast 提示", "OK")
    if modified:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        log("前端 JS 已更新", "OK")
    else:
        log("前端 JS 无需修改", "INFO")
    return True

def print_next_steps():
    print("\n[6/6] 完成！下一步：")
    print("  1. 强制刷新页面：Ctrl + F5")
    print("  2. 按 F12 打开浏览器控制台")
    print("  3. 上传一个有声音的视频文件")
    print("  4. 查看 Console 标签页的日志：")
    print("     - [Transcribe] 开始上传 ...  →  前端已发起请求")
    print("     - 如果看到红色错误 → 截图发给我")
    print(f"\n  转写服务地址：<ADDRESS_REMOVED>

if __name__ == '__main__':
    print("=" * 60)
    print(" 语音转写问题一键诊断 + 修复")
    print("=" * 60)
    kill_old()
    if not start_service():
        print("\n❌ 服务启动失败，请检查 transcribe_server.py 是否有语法错误")
        sys.exit(1)
    if not test_api():
        print("\n❌ API 测试失败，请检查后端日志")
        sys.exit(1)
    check_frontend()
    fix_frontend()
    print_next_steps()
