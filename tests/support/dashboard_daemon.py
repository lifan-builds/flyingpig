"""Mock daemon for deterministic helper dashboard tests."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Flying Pig Helper Dashboard Mock Daemon")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/dashboard", StaticFiles(directory=ROOT / "dashboard", html=True), name="dashboard")


@app.get("/")
async def dashboard_root():
    return RedirectResponse(url="/dashboard/")

mock_browser_connected = False
mock_work_window_url = "https://support.ouraring.com/hc/en-us/articles/360047222554-Contact-Us"
mock_state = {
    "type": "state",
    "status": "ready_to_start",
    "running": False,
    "needs_input": False,
    "site": None,
    "message": "Ready to start a supervised customer-service task.",
    "step": None,
    "updated_at": None,
    "started_at": None,
    "finished_at": None,
    "transcript": None,
    "result": None,
    "pending_request": None,
    "timing_spans": [],
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def apply_state(**changes) -> dict:
    mock_state.update(changes)
    mock_state["type"] = "state"
    mock_state["updated_at"] = now()
    return dict(mock_state)


def timing_span(name: str, label: str, duration_ms: float, status: str = "ok") -> dict:
    return {
        "type": "timing_span",
        "name": name,
        "label": label,
        "duration_ms": duration_ms,
        "status": status,
        "timestamp": now(),
        "metadata": {},
    }


def add_timing_span(span: dict) -> dict:
    spans = list(mock_state.get("timing_spans") or [])
    spans.append(span)
    apply_state(timing_spans=spans)
    return span


def checkpoint_request() -> dict:
    return {
        "type": "decision_checkpoint",
        "checkpoint": {
            "checkpoint_id": "cp_mock",
            "type": "strategy_pivot",
            "summary": "No retention offer is available.",
            "recommended_option_id": "close_card",
            "options": [
                {
                    "id": "close_card",
                    "label": "Close card",
                    "consequence": "Proceed to cancellation disclosure.",
                    "message_to_send": "I would like to proceed toward closing.",
                },
                {
                    "id": "stop",
                    "label": "Stop here",
                    "consequence": "No account change is made.",
                    "message_to_send": "Thanks, I will decide later.",
                },
            ],
        },
    }


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/model/settings")
async def model_settings():
    return {
        "ok": True,
        "default_model": "cliproxyapi",
        "providers": [
            {
                "id": "cliproxyapi",
                "label": "CLIProxyAPI",
                "configured": True,
                "help": "Uses the mock CLIProxyAPI settings.",
            },
            {
                "id": "claude",
                "label": "Claude",
                "configured": False,
                "help": "Used for Claude test runs.",
            },
            {
                "id": "openai",
                "label": "OpenAI",
                "configured": False,
                "help": "Used for OpenAI test runs.",
            },
            {
                "id": "gemini-flash",
                "label": "Gemini",
                "configured": False,
                "help": "Used for Gemini test runs.",
            },
        ],
    }


@app.post("/model/settings")
async def model_settings_update(request: Request):
    payload = await request.json()
    provider = payload.get("provider") or "cliproxyapi"
    response = await model_settings()
    for item in response["providers"]:
        if item["id"] == provider:
            item["configured"] = not payload.get("clear_key")
    response["default_model"] = payload.get("default_model") or "cliproxyapi"
    return response


@app.post("/browser/launch")
async def browser_launch(request: Request):
    global mock_browser_connected, mock_work_window_url

    payload = await request.json()
    if payload.get("chrome_profile") != "dedicated":
        return {
            "ok": False,
            "error": f"expected dedicated work profile, got {payload.get('chrome_profile')}",
        }
    if not all(payload.get(key) for key in ("window_width", "window_height")):
        return {
            "ok": False,
            "error": "expected side-by-side work-window placement hints",
        }
    mock_browser_connected = True
    mock_work_window_url = payload.get("initial_url") or mock_work_window_url
    span = add_timing_span(timing_span("launch", "Work window launch", 42.0))
    return {
        "ok": True,
        "cdp_url": "http://127.0.0.1:9335",
        "current_url": mock_work_window_url,
        "current_title": "Mock work window",
        "message": "MOCK-CHROME-READY",
        "timing_span": span,
    }


@app.get("/browser/status")
async def browser_status():
    return {
        "ok": True,
        "connected": mock_browser_connected,
        "cdp_url": "http://127.0.0.1:9335",
        "current_url": mock_work_window_url if mock_browser_connected else None,
        "current_title": "Mock work window" if mock_browser_connected else None,
        "message": "MOCK-BROWSER-CONNECTED"
        if mock_browser_connected
        else "MOCK-BROWSER-DISCONNECTED",
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_text(json.dumps({"type": "ready"}))
    await ws.send_text(json.dumps(dict(mock_state)))
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "list_sites":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "sites",
                            "items": [
                                {
                                    "id": "amex",
                                    "label": "American Express",
                                    "chat_url": (
                                        "https://www.americanexpress.com/us/customer-service/"
                                    ),
                                    "requires_login": True,
                                    "templates": [],
                                },
                                {
                                    "id": "oura",
                                    "label": "Oura Ring",
                                    "chat_url": (
                                        "https://support.ouraring.com/hc/en-us/articles/"
                                        "360047222554-Contact-Us"
                                    ),
                                    "requires_login": False,
                                    "templates": [],
                                },
                                {
                                    "id": "generic",
                                    "label": "Generic (auto-detect chat)",
                                    "chat_url": "",
                                    "requires_login": False,
                                    "templates": [],
                                },
                            ],
                        }
                    )
                )
            elif mtype == "resolve":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "resolved",
                            "url": msg.get("url", ""),
                            "site": "amex",
                        }
                    )
                )
            elif mtype == "start":
                preflight_span = add_timing_span(
                    timing_span("preflight", "Pre-flight safety gate", 7.0)
                )
                await ws.send_text(json.dumps(preflight_span))
                if "checkpoint" in (msg.get("task") or "").lower():
                    request = checkpoint_request()
                    await ws.send_text(json.dumps(request))
                    await ws.send_text(
                        json.dumps(
                            apply_state(
                                status="needs_input",
                                running=True,
                                needs_input=True,
                                site="amex",
                                message=request["checkpoint"]["summary"],
                                pending_request=request,
                                started_at=now(),
                                finished_at=None,
                            )
                        )
                    )
                    continue
                if "cancel" in (msg.get("task") or "").lower():
                    await ws.send_text(
                        json.dumps(
                            apply_state(
                                status="running",
                                running=True,
                                needs_input=False,
                                site="amex",
                                message="MOCK-CANCEL-RUNNING",
                                step=1,
                                started_at=now(),
                                finished_at=None,
                                pending_request=None,
                            )
                        )
                    )
                    continue
                await ws.send_text(
                    json.dumps(
                        apply_state(
                            status="running",
                            running=True,
                            needs_input=False,
                            site="amex",
                            message="mock run started",
                            step=None,
                            started_at=now(),
                            finished_at=None,
                            transcript=None,
                            result=None,
                            pending_request=None,
                        )
                    )
                )
                await ws.send_text(json.dumps({"type": "status", "text": "mock run started"}))
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "event": {
                                "step": 1,
                                "phase": "complete",
                                "message": f"target {msg.get('target_url') or msg.get('url')}",
                            },
                        }
                    )
                )
                step_span = add_timing_span(
                    timing_span("browser_use_step", "Browser-use step", 83.0)
                )
                model_span = add_timing_span(
                    timing_span("model_call", "Model planning step", 83.0)
                )
                await ws.send_text(json.dumps(step_span))
                await ws.send_text(json.dumps(model_span))
                await asyncio.sleep(0.1)
                result_timing = list(mock_state["timing_spans"])
                timing_summary = {
                    "total_ms": sum(span["duration_ms"] for span in result_timing),
                    "span_count": len(result_timing),
                    "by_name_ms": {span["name"]: span["duration_ms"] for span in result_timing},
                }
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "result_ready",
                            "status": "success",
                            "summary": "MOCK-RUN-OK dashboard protocol completed.",
                            "outcome_summary": "MOCK-RUN-OK dashboard protocol completed.",
                            "steps": 1,
                            "duration": 0.1,
                            "timing_spans": result_timing,
                            "timing_summary": timing_summary,
                        }
                    )
                )
                await ws.send_text(
                    json.dumps(
                        apply_state(
                            status="success",
                            running=False,
                            needs_input=False,
                            site="amex",
                            message="MOCK-RUN-OK dashboard protocol completed.",
                            step=1,
                            started_at=mock_state.get("started_at") or now(),
                            finished_at=now(),
                            transcript="recordings/mock.json",
                            result={
                                "status": "success",
                                "summary": "MOCK-RUN-OK dashboard protocol completed.",
                                "outcome_summary": "MOCK-RUN-OK dashboard protocol completed.",
                                "steps": 1,
                                "duration": 0.1,
                                "transcript": "recordings/mock.json",
                                "timing_spans": result_timing,
                                "timing_summary": timing_summary,
                            },
                            pending_request=None,
                            timing_spans=result_timing,
                        )
                    )
                )
            elif mtype == "answer":
                if msg.get("payload", {}).get("checkpoint_id") == "cp_mock":
                    await ws.send_text(json.dumps({"type": "status", "text": "answer received"}))
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "result",
                                "status": "success",
                                "summary": "MOCK-CHECKPOINT-OK decision selected.",
                                "steps": 1,
                                "duration": 0.1,
                            }
                        )
                    )
                    await ws.send_text(
                        json.dumps(
                            apply_state(
                                status="success",
                                running=False,
                                needs_input=False,
                                message="MOCK-CHECKPOINT-OK decision selected.",
                                step=1,
                                finished_at=now(),
                                result={
                                    "status": "success",
                                    "summary": "MOCK-CHECKPOINT-OK decision selected.",
                                    "steps": 1,
                                    "duration": 0.1,
                                },
                                pending_request=None,
                            )
                        )
                    )
                    continue
                await ws.send_text(json.dumps({"type": "status", "text": "answer received"}))
            elif mtype == "huca":
                await ws.send_text(json.dumps({"type": "status", "text": "HUCA restart"}))
                await ws.send_text(
                    json.dumps(
                        apply_state(
                            status="starting",
                            running=True,
                            needs_input=False,
                            site=msg.get("site") or "amex",
                            message="MOCK-HUCA-RESTARTING",
                            step=None,
                            started_at=now(),
                            finished_at=None,
                            pending_request=None,
                        )
                    )
                )
                await asyncio.sleep(0.1)
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "result",
                            "status": "success",
                            "summary": "MOCK-HUCA-OK fresh chat requested.",
                            "steps": 1,
                            "duration": 0.1,
                        }
                    )
                )
                await ws.send_text(
                    json.dumps(
                        apply_state(
                            status="success",
                            running=False,
                            needs_input=False,
                            message="MOCK-HUCA-OK fresh chat requested.",
                            step=1,
                            finished_at=now(),
                            result={
                                "status": "success",
                                "summary": "MOCK-HUCA-OK fresh chat requested.",
                                "steps": 1,
                                "duration": 0.1,
                            },
                            pending_request=None,
                        )
                    )
                )
            elif mtype == "cancel":
                await ws.send_text(json.dumps({"type": "status", "text": "cancelled"}))
                await ws.send_text(
                    json.dumps(
                        apply_state(
                            status="cancelled",
                            running=False,
                            needs_input=False,
                            message="MOCK-CANCELLED",
                            finished_at=now(),
                            pending_request=None,
                        )
                    )
                )
            else:
                await ws.send_text(
                    json.dumps({"type": "error", "text": f"unknown message type: {mtype}"})
                )
    except WebSocketDisconnect:
        return
