"""同步测试：直接在主线程运行 transcribe_server 的关键代码"""
import sys, os, time, threading

# 模拟 Flask 的 jobs dict
jobs = {}

def _track_transcription_progress(job_id, duration):
    log_path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\tracker.log'
    def _log(msg):
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    import time as _t
    estimated_seconds = max(8, duration * 1.5)
    start_time = _t.time()
    _log(f"[Tracker] 启动 job={job_id} estimated={estimated_seconds:.1f}s")
    i = 0
    while i < 5:
        _t.sleep(0.5)
        elapsed = _t.time() - start_time
        job = jobs.get(job_id)
        if not job:
            _log(f"[Tracker] job={job_id} 不存在，退出")
            break
        status = job.get("status", "")
        if status in ("done", "error"):
            _log(f"[Tracker] job={job_id} 状态={status}，退出")
            break
        job["progress"] = min(80, round((elapsed / estimated_seconds) * 40 + 40, 1))
        job["estimated_remaining"] = round(max(0, estimated_seconds - elapsed), 1)
        _log(f"[Tracker] job={job_id} elapsed={elapsed:.1f}s progress={job['progress']}%")
        i += 1
    _log(f"[Tracker] 完成 5 次迭代")

# 模拟 run_transcription（在 daemon 线程中）
def run_transcription(job_id, video_path, duration):
    log_path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\tracker.log'
    jobs[job_id] = {"status": "transcribing", "progress": 40}
    
    with open(log_path, 'a', encoding='utf-8') as lf:
        lf.write(f"[Main] job={job_id} 设置 status=transcribing, progress=40\n")
    
    # 启动 tracker
    tracker = threading.Thread(
        target=_track_transcription_progress,
        args=(job_id, duration),
        daemon=True
    )
    tracker.start()
    
    with open(log_path, 'a', encoding='utf-8') as lf:
        lf.write(f"[Main] job={job_id} tracker.start() 返回, alive={tracker.is_alive()}, ident={tracker.ident}\n")
    
    # 模拟转写耗时
    time.sleep(3)
    
    jobs[job_id]["status"] = "analyzing"
    jobs[job_id]["progress"] = 80
    with open(log_path, 'a', encoding='utf-8') as lf:
        lf.write(f"[Main] job={job_id} transcription done, status=analyzing\n")

# 主程序
log_path = r'C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer\tracker.log'
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('[TEST] 开始测试\n')

job_id = 'test-sync-123'
t = threading.Thread(target=run_transcription, args=(job_id, 'dummy.mp4', 45.0), daemon=True)
t.start()

# 主线程轮询
for i in range(8):
    time.sleep(0.5)
    job = jobs.get(job_id, {})
    print(f"[Poll {i+1}] status={job.get('status')} progress={job.get('progress')} eta={job.get('estimated_remaining')}")
    if job.get('status') == 'analyzing':
        print('Done!')
        break

time.sleep(1)
with open(log_path, 'r', encoding='utf-8') as f:
    print('\n=== tracker.log 内容 ===')
    print(f.read())
