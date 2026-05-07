"""Mock daemon for deterministic Chrome extension side-panel tests."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Flying Pig Extension Mock Daemon")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_text(json.dumps({"type": "ready"}))
    await ws.send_text(
        json.dumps({
            "type": "state",
            "status": "idle",
            "running": False,
            "needs_input": False,
            "site": None,
            "message": "Idle",
            "step": None,
            "updated_at": datetime.now(UTC).isoformat(),
            "started_at": None,
            "finished_at": None,
            "transcript": None,
            "result": None,
        })
    )
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "resolve":
                await ws.send_text(
                    json.dumps({
                        "type": "resolved",
                        "url": msg.get("url", ""),
                        "site": "amex",
                    })
                )
            elif mtype == "start":
                await ws.send_text(
                    json.dumps({
                        "type": "state",
                        "status": "running",
                        "running": True,
                        "needs_input": False,
                        "site": "amex",
                        "message": "mock run started",
                        "step": None,
                        "updated_at": datetime.now(UTC).isoformat(),
                        "started_at": datetime.now(UTC).isoformat(),
                        "finished_at": None,
                        "transcript": None,
                        "result": None,
                    })
                )
                await ws.send_text(json.dumps({"type": "status", "text": "mock run started"}))
                await ws.send_text(
                    json.dumps({
                        "type": "progress",
                        "event": {
                            "step": 1,
                            "phase": "complete",
                            "message": f"target {msg.get('target_url') or msg.get('url')}",
                        },
                    })
                )
                await asyncio.sleep(0.1)
                await ws.send_text(
                    json.dumps({
                        "type": "result",
                        "status": "success",
                        "summary": "MOCK-RUN-OK side panel protocol completed.",
                        "steps": 1,
                        "duration": 0.1,
                    })
                )
                await ws.send_text(
                    json.dumps({
                        "type": "state",
                        "status": "success",
                        "running": False,
                        "needs_input": False,
                        "site": "amex",
                        "message": "MOCK-RUN-OK side panel protocol completed.",
                        "step": 1,
                        "updated_at": datetime.now(UTC).isoformat(),
                        "started_at": datetime.now(UTC).isoformat(),
                        "finished_at": datetime.now(UTC).isoformat(),
                        "transcript": "recordings/mock.json",
                        "result": {
                            "status": "success",
                            "summary": "MOCK-RUN-OK side panel protocol completed.",
                            "steps": 1,
                            "duration": 0.1,
                            "transcript": "recordings/mock.json",
                        },
                    })
                )
            elif mtype == "answer":
                await ws.send_text(json.dumps({"type": "status", "text": "answer received"}))
            elif mtype == "cancel":
                await ws.send_text(json.dumps({"type": "status", "text": "cancelled"}))
            else:
                await ws.send_text(
                    json.dumps({"type": "error", "text": f"unknown message type: {mtype}"})
                )
    except WebSocketDisconnect:
        return
