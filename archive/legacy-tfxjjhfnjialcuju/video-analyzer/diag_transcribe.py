"""
诊断转写服务状态
"""
import requests
import time
import subprocess
import os

PORT = 8766
BASE = f"http://127.0.0.1:{PORT}"

print("=" * 60)
print("语音转写服务诊断")
print("=" * 60)

# 1. 检查服务是否在线
print("\n[1/5] 检查服务在线状态...")
try:
    resp = requests.get(f"{BASE}/api/video-meta", timeout=5)
    print(f"  ✅ 服务在线 (状态码 {resp.status_code})")
except Exception as e:
    print(f"  ❌ 服务离线: {e}")
    print("  请先启动转写服务: python transcribe_server.py")
    exit(1)

# 2. 检查 Whisper 模型是否加载
print("\n[2/5] 检查 Whisper 模型...")
# 通过发起一个无效的转写请求来触发模型加载检查
# 或者检查进程内存占用
try:
    result = subprocess.run(
        f"netstat -ano | findstr :{PORT}",
        shell=True, capture_output=True, text=True
    )
    if result.stdout:
        lines = [l for l in result.stdout.strip().split('\n') if 'LISTENING' in l]
        if lines:
            pid = lines[0].strip().split()[-1]
            print(f"  服务进程 PID: {pid}")
            # 检查进程内存
            mem_result = subprocess.run(
                f"tasklist /fi \"PID eq {pid}\" /fo csv | findstr python",
                shell=True, capture_output=True, text=True
            )
            if mem_result.stdout:
                print(f"  进程信息: {mem_result.stdout.strip()}")
    else:
        print("  ⚠️ 无法获取进程信息")
except Exception as e:
    print(f"  ⚠️ 检查进程失败: {e}")

# 3. 检查音频提取工具
print("\n[3/5] 检查音频提取工具 (imageio-ffmpeg)...")
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"  ✅ ffmpeg 路径: {ffmpeg_exe}")
    # 测试 ffmpeg 是否可执行
    test = subprocess.run(
        f'"{ffmpeg_exe}" -version',
        shell=True, capture_output=True, text=True, timeout=10
    )
    if test.returncode == 0:
        version = test.stdout.split('\n')[0]
        print(f"  ✅ ffmpeg 版本: {version}")
    else:
        print(f"  ❌ ffmpeg 执行失败")
except Exception as e:
    print(f"  ❌ imageio-ffmpeg 不可用: {e}")
    print("  请安装: pip install imageio-ffmpeg")

# 4. 测试转写 API（用测试视频）
print("\n[4/5] 测试转写 API...")
TEST_VIDEO = r"C:\Users\EDY\Videos\data\收藏\视频\7080470245349068032.mp4"
if os.path.exists(TEST_VIDEO):
    print(f"  测试视频: {TEST_VIDEO}")
    print("  ⚠️ 注意: 此视频无音轨，转写会失败（预期行为）")
    print("  建议使用有声视频测试转写功能")
else:
    print(f"  ⚠️ 测试视频不存在: {TEST_VIDEO}")

# 5. 建议
print("\n[5/5] 诊断建议...")
print("""
  如果转写失败，请检查：
  1. 视频是否有音轨？
     - 用 PotPlayer / VLC 打开视频，查看"音频"菜单
     - 或运行: ffprobe video.mp4 2>&1 | findstr "Audio"
  
  2. 转写服务日志（运行 transcribe_server.py 的窗口）有无报错？
     - 查看是否显示 "Model loaded" 或错误信息
  
  3. 浏览器控制台（F12）有无报错？
     - 查看 Network 标签页，转写 API 请求是否成功
  
  4. 小视频（< 1分钟）测试：
     - 上传一个短的有声视频，观察转写进度
""")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
