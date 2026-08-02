"""
WebSocket endpoint for real-time job progress updates.
Resolves Bug #11 (no timeout/retry) by providing real-time push instead of polling.
Workers publish progress to Redis pub/sub, WebSocket subscribes and forwards to browser.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis

from app.config import get_settings
from app.core.logging import get_logger

router = APIRouter(tags=["websocket"])
log = get_logger("websocket")
settings = get_settings()


@router.websocket("/api/v1/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str) -> None:
    """
    WebSocket endpoint for real-time job progress updates.

    Flow:
    1. Client connects to ws://host/api/v1/ws/jobs/{job_id}
    2. Server subscribes to Redis pub/sub channel "job:{job_id}"
    3. Celery worker publishes progress updates to the channel
    4. Server forwards messages to the client via WebSocket
    5. Client receives {progress, message, status} JSON messages

    The connection stays open until the job completes or the client disconnects.
    """
    await websocket.accept()
    log.info("ws_connected", job_id=job_id)

    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"job:{job_id}")

    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "job_id": job_id,
            "message": "WebSocket connection established",
        }))

        # Listen for messages from Redis pub/sub
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                # Forward to WebSocket client
                await websocket.send_text(data)

                # Check if this is a completion or error message
                try:
                    parsed = json.loads(data)
                    if parsed.get("status") in ("completed", "failed", "cancelled"):
                        log.info("ws_job_ended", job_id=job_id, status=parsed["status"])
                        # Send a close message and break
                        await websocket.send_text(json.dumps({
                            "type": "close",
                            "message": "Job finished, closing connection",
                        }))
                        break
                except (json.JSONDecodeError, TypeError):
                    pass

    except WebSocketDisconnect:
        log.info("ws_disconnected", job_id=job_id)
    except Exception as e:
        log.error("ws_error", job_id=job_id, error=str(e))
    finally:
        try:
            await pubsub.unsubscribe(f"job:{job_id}")
        except Exception:
            pass
        try:
            await redis.aclose()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        log.info("ws_closed", job_id=job_id)
