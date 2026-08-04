"""
Video Content Analyzer - SQLite 持久化层

任务/分析结果存储，解决"服务重启数据全丢"问题。
- 数据库文件：backend/data/analyzer.db（自动创建目录）
- 标准库 sqlite3，零额外依赖
- 三张表：
  transcribe_jobs  转写任务（含结果）
  analyze_jobs     文案分析任务（LLM）
  analysis_results 智能分析结果（hook/ocr/info-density/visual-anchor）

线程安全：sqlite3 连接默认 check_same_thread=False + 全局写锁，
配合 Flask threaded 模式使用。
"""

import json
import os
import sqlite3
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # backend/
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "analyzer.db"

_write_lock = threading.Lock()

# ── 建表 ──
_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcribe_jobs (
    id          TEXT PRIMARY KEY,
    filename    TEXT,
    duration    REAL,
    status      TEXT,
    progress    INTEGER,
    detail      TEXT,
    error       TEXT,
    result      TEXT,          -- JSON 字符串（转写结果）
    video_path  TEXT,
    created_at  REAL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS analyze_jobs (
    id          TEXT PRIMARY KEY,
    model       TEXT,
    status      TEXT,
    progress    INTEGER,
    error       TEXT,
    result      TEXT,          -- JSON 字符串（文案分析结果）
    created_at  REAL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     TEXT,
    kind       TEXT,           -- hook / ocr / info_density / visual_anchor
    result     TEXT,           -- JSON 字符串
    created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_analysis_job ON analysis_results(job_id);
"""


def get_conn() -> sqlite3.Connection:
    """获取线程安全的连接（每线程独立连接，避免共享连接并发问题）"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据库（建目录 + 建表）"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(_SCHEMA)
    print(f"[DB] SQLite 初始化完成: {DB_PATH}")


# ── 转写任务 ──

def save_transcribe_job(job_id: str, data: dict) -> None:
    """插入或更新一条转写任务记录（按 id upsert）"""
    with _write_lock, get_conn() as conn:
        conn.execute(
            """
            INSERT INTO transcribe_jobs
                (id, filename, duration, status, progress, detail, error, result, video_path, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status, progress=excluded.progress,
                detail=excluded.detail, error=excluded.error,
                result=excluded.result, video_path=excluded.video_path,
                finished_at=excluded.finished_at
            """,
            (
                job_id,
                data.get("filename"),
                data.get("duration"),
                data.get("status"),
                data.get("progress"),
                data.get("detail"),
                data.get("error"),
                _dumps(data.get("result")),
                data.get("video_path"),
                data.get("start_time") or data.get("created_at"),
                data.get("finished_at"),
            ),
        )


def load_transcribe_jobs() -> dict:
    """启动时恢复全部转写任务到内存字典（仅保留必要字段，跳过超大 result）"""
    jobs = {}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transcribe_jobs WHERE status IN ('done','error','audio_ready','starting')"
        ).fetchall()
    for r in rows:
        result = _loads(r["result"])
        jobs[r["id"]] = {
            "status": r["status"],
            "progress": r["progress"] or 0,
            "detail": r["detail"] or "",
            "result": result,
            "error": r["error"],
            "video_path": r["video_path"] or "",
            "filename": r["filename"] or "",
            "duration": r["duration"],
            "start_time": r["created_at"] or 0,
            "finished_at": r["finished_at"],
        }
    return jobs


def query_transcribe_history(limit: int = 50) -> list:
    """历史转写任务列表（新的在前），用于前端历史记录"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transcribe_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "job_id": r["id"],
            "filename": r["filename"],
            "duration": r["duration"],
            "status": r["status"],
            "progress": r["progress"],
            "error": r["error"],
            "created_at": r["created_at"],
            "finished_at": r["finished_at"],
        })
    return out


# ── 文案分析任务 ──

def save_analyze_job(job_id: str, data: dict) -> None:
    """插入或更新一条文案分析任务（按 id upsert）"""
    with _write_lock, get_conn() as conn:
        conn.execute(
            """
            INSERT INTO analyze_jobs (id, model, status, progress, error, result, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                model=excluded.model, status=excluded.status,
                progress=excluded.progress, error=excluded.error,
                result=excluded.result, finished_at=excluded.finished_at
            """,
            (
                job_id,
                data.get("model"),
                data.get("status"),
                data.get("progress"),
                data.get("error"),
                _dumps(data.get("result")),
                data.get("start_time") or data.get("created_at"),
                data.get("finished_at"),
            ),
        )


def load_analyze_jobs() -> dict:
    """启动时恢复文案分析任务到内存字典"""
    jobs = {}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM analyze_jobs WHERE status IN ('done','error')"
        ).fetchall()
    for r in rows:
        result = _loads(r["result"])
        jobs[r["id"]] = {
            "status": r["status"],
            "progress": r["progress"] or 0,
            "result": result or {},
            "error": r["error"],
            "model": r["model"],
            "start_time": r["created_at"] or 0,
        }
    return jobs


def query_analyze_history(limit: int = 50) -> list:
    """历史文案分析任务列表（新的在前）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM analyze_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "job_id": r["id"],
            "model": r["model"],
            "status": r["status"],
            "error": r["error"],
            "created_at": r["created_at"],
            "finished_at": r["finished_at"],
        })
    return out


# ── 智能分析结果 ──

def save_analysis_result(job_id: str, kind: str, result: dict) -> None:
    """保存一条智能分析结果（hook/ocr/info_density/visual_anchor）"""
    with _write_lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO analysis_results (job_id, kind, result, created_at) VALUES (?, ?, ?, ?)",
            (job_id, kind, _dumps(result), time_now()),
        )


def query_analysis_results(job_id: str = None, limit: int = 100) -> list:
    """查询智能分析结果，可按 job_id 过滤"""
    sql = "SELECT * FROM analysis_results"
    params: tuple = ()
    if job_id:
        sql += " WHERE job_id = ?"
        params = (job_id,)
    sql += " ORDER BY id DESC LIMIT ?"
    params = params + (limit,)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "job_id": r["job_id"],
            "kind": r["kind"],
            "result": _loads(r["result"]),
            "created_at": r["created_at"],
        })
    return out


# ── 工具 ──

def _dumps(obj) -> str:
    """dict → JSON 字符串（None → NULL）"""
    if obj is None:
        return None
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def _loads(s) -> dict:
    """JSON 字符串 → dict（空/损坏 → None）"""
    if not s:
        return None
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return None


def time_now() -> float:
    import time
    return time.time()


if __name__ == "__main__":
    # 简单自测
    init_db()
    save_transcribe_job("test1", {
        "filename": "demo.mp4", "duration": 30.0, "status": "done",
        "progress": 100, "result": {"text": "你好"}, "start_time": time_now(),
    })
    assert query_transcribe_history(5)[0]["filename"] == "demo.mp4"
    save_analysis_result("test1", "hook", {"score": 85})
    assert query_analysis_results("test1")[0]["result"]["score"] == 85
    # 清理测试数据
    with get_conn() as conn:
        conn.execute("DELETE FROM transcribe_jobs WHERE id='test1'")
        conn.execute("DELETE FROM analysis_results WHERE job_id='test1'")
    print("[DB] 自测通过 ✓")
