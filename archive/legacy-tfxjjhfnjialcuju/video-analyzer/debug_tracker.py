"""独立测试 tracker 线程是否能更新共享 jobs 字典"""
import sys, time, threading

# 模拟 transcribe_server 中的 jobs 字典
jobs = {}

def _track_transcription_progress(job_id, duration):
    import time, math
    sys.stderr.write(f"[Tracker] 启动 job={job_id} estimated={duration * 1.5:.1f}s\n")
    sys.stderr.flush()
    start_time = time.time()
    estimated_seconds = max(8, duration * 1.5)
    while True:
        time.sleep(0.5)
        elapsed = time.time() - start_time
        job = jobs.get(job_id)
        if not job:
            sys.stderr.write(f"[Tracker] job={job_id} 不存在\n")
            break
        status = job.get("status", "")
        if status in ("done", "error", "no_audio"):
            sys.stderr.write(f"[Tracker] job={job_id} 状态={status} 退出\n")
            break
        if elapsed < 0.6:
            continue
        raw_progress = (elapsed / estimated_seconds) * 40 + 40
        progress = min(80, round(raw_progress, 1))
        remaining = max(0, estimated_seconds - elapsed)
        job["progress"] = progress
        job["estimated_remaining"] = round(remaining, 1)
        sys.stderr.write(f"[Tracker] job={job_id} elapsed={elapsed:.1f}s progress={progress}% eta={remaining:.1f}s\n")
        sys.stderr.flush()
        if elapsed > estimated_seconds * 2:
            break

# 模拟 Flask route handler
job_id = "test-123"
jobs[job_id] = {"status": "transcribing", "progress": 40}

# 启动 tracker
t = threading.Thread(target=_track_transcription_progress, args=(job_id, 45.0), daemon=True)
t.start()

# 主线程轮询 jobs
for i in range(6):
    time.sleep(1)
    job = jobs.get(job_id)
    if job:
        print(f"[Main] {i+1}s: progress={job.get('progress')} eta={job.get('estimated_remaining')} status={job.get('status')}")
    else:
        print(f"[Main] {i+1}s: job 不存在")

time.sleep(2)
print("测试完成")
