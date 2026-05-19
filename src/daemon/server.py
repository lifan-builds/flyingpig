"""WebSocket daemon that connects a frontend (dashboard or CLI) to AgentBrain.

Protocol (JSON per frame, both directions):

  Client -> Daemon:
    {"type": "start", "site": "amex", "template": "negotiate_fee",
     "task": "...", "cdp_url": "http://127.0.0.1:9222"}
    {"type": "answer", "text": "..."}                  # response to a "question"
    {"type": "cancel"}
    {"type": "list_sites"}

  Daemon -> Client:
    {"type": "sites", "items": [...]}
    {"type": "status", "text": "..."}                  # human-readable progress
    {"type": "progress", "event": {...}}                # step-level agent progress
    {"type": "question", "question": "...", "reason": "..."}
    {"type": "decision_checkpoint", "checkpoint": {...}}
    {"type": "result", "status": "success|partial|failed|needs_input",
                       "summary": "...", "steps": N, "duration": S}
    {"type": "error", "text": "..."}
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent.brain import AgentBrain, TaskStatus
from src.agent.browser_runtime import (
    ChromeLaunchConfig,
    debugger_is_ready,
    debugger_page_info,
    launch_cdp_chrome,
)
from src.daemon.run_session import (
    RunStateStore,
    now_iso,
    progress_message,
    protocol_event_for_request,
    request_message,
    result_payload,
)
from src.sites.registry import get_site_adapter, list_sites, resolve_from_url
from src.sites.task_templates import get_templates

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT / "dashboard"


class BrowserLaunchRequest(BaseModel):
    site: str = "generic"
    cdp_port: int = 9222
    chrome_profile: str = "dedicated"
    chrome_user_data_dir: str | None = None
    initial_url: str | None = None
    window_width: int = 1120
    window_height: int = 900
    window_left: int = 560
    window_top: int = 80


class BrowserStatusRequest(BaseModel):
    cdp_url: str = "http://127.0.0.1:9222"


class RunStartRequest(BaseModel):
    site: str | None = "generic"
    url: str = ""
    template: str | None = None
    task: str
    cdp_url: str | None = None
    target_url: str | None = None
    model: str | None = None
    fallback_model: str | None = None
    max_steps: int = 80
    navigate_on_attach: bool = False


class RunAnswerRequest(BaseModel):
    text: str = ""
    payload: dict | None = None


class RunManager:
    """Owns the active agent run independently of dashboard connections."""

    def __init__(self):
        self.brain: AgentBrain | None = None
        self.agent_task: asyncio.Task | None = None
        self.progress_task: asyncio.Task | None = None
        self.questions_task: asyncio.Task | None = None
        self.sessions: set[Session] = set()
        self.lock = asyncio.Lock()
        self.state = RunStateStore()

    def attach(self, session: Session) -> None:
        self.sessions.add(session)

    def detach(self, session: Session) -> None:
        self.sessions.discard(session)

    async def send_snapshot(self, session: Session) -> None:
        await session.send(**self.state.snapshot())

    async def broadcast(self, **payload) -> None:
        stale = []
        for session in self.sessions:
            try:
                await session.send(**payload)
            except Exception:
                stale.append(session)
        for session in stale:
            self.detach(session)

    async def set_state(self, **changes) -> None:
        await self.broadcast(**self.state.apply(**changes))

    def _sites_payload(self) -> list[dict]:
        out = []
        for site in list_sites():
            adapter = get_site_adapter(site)
            templates = get_templates(site)
            out.append(
                {
                    "id": site,
                    "label": adapter.name,
                    "chat_url": adapter.chat_url,
                    "requires_login": adapter.requires_login,
                    "templates": [
                        {"id": t.id, "label": t.name, "description": t.description}
                        for t in templates
                    ],
                }
            )
        return out

    async def start(self, msg: dict) -> None:
        async with self.lock:
            if self.agent_task and not self.agent_task.done():
                await self.broadcast(type="error", text="agent already running")
                return

            url = msg.get("url") or ""
            requested_site = msg.get("site")
            site = resolve_from_url(url) if requested_site in (None, "", "auto") else requested_site
            if not site:
                await self.broadcast(
                    type="error",
                    text=(
                        "Could not resolve the work window. "
                        "Launch a customer-service work window first."
                    ),
                )
                await self.set_state(
                    status="idle",
                    running=False,
                    needs_input=False,
                    message="Open a customer-service tab first.",
                    site=None,
                )
                return

            template = msg.get("template") or None
            task = msg.get("task") or ""
            cdp_url = msg.get("cdp_url") or None
            target_url = msg.get("target_url") or url or None

            self.brain = AgentBrain(
                site=site,
                headless=False,
                input_mode="api",
                model=msg.get("model"),
                fallback_model=msg.get("fallback_model"),
                cdp_url=cdp_url,
                target_url=target_url,
                navigate_on_attach=bool(msg.get("navigate_on_attach")),
            )
            started_at = now_iso()
            await self.broadcast(type="status", text=f"using adapter: {site}")
            await self.set_state(
                status="starting",
                running=True,
                needs_input=False,
                site=site,
                message=f"Starting agent for {site}",
                step=None,
                started_at=started_at,
                finished_at=None,
                transcript=None,
                result=None,
                pending_request=None,
            )
            self.agent_task = asyncio.create_task(
                self._run_agent(
                    task=task,
                    template_id=template,
                    max_steps=msg.get("max_steps", 30),
                )
            )
            self.questions_task = asyncio.create_task(self._poll_questions())
            self.progress_task = asyncio.create_task(self._poll_progress())

    async def _run_agent(self, *, task: str, template_id: str | None, max_steps: int) -> None:
        try:
            assert self.brain is not None
            result = await self.brain.execute(
                task=task, max_steps=max_steps, template_id=template_id
            )
            payload = result_payload(result)
            await self.broadcast(**payload)
            await self.set_state(
                status=payload["status"],
                running=False,
                needs_input=False,
                message=result.summary,
                step=result.steps_taken,
                finished_at=now_iso(),
                transcript=payload["transcript"],
                result=payload,
                pending_request=None,
            )
        except asyncio.CancelledError:
            await self.set_state(
                status="cancelled",
                running=False,
                needs_input=False,
                message="Cancelled",
                finished_at=now_iso(),
                pending_request=None,
            )
            raise
        except Exception as e:
            logger.exception("agent run failed")
            await self.broadcast(type="error", text=f"{type(e).__name__}: {e}")
            await self.set_state(
                status="error",
                running=False,
                needs_input=False,
                message=f"{type(e).__name__}: {e}",
                finished_at=now_iso(),
                pending_request=None,
            )

    async def _poll_questions(self) -> None:
        last_seen: str | None = None
        while self.agent_task and not self.agent_task.done():
            await asyncio.sleep(0.3)
            if not self.brain:
                continue
            request = getattr(self.brain.input_handler, "pending_request", None)
            request_key = json.dumps(request, sort_keys=True) if request else None
            if request and request_key != last_seen:
                last_seen = request_key
                await self.broadcast(**protocol_event_for_request(request))
                await self.set_state(
                    status="needs_input",
                    running=True,
                    needs_input=True,
                    message=request_message(request),
                    pending_request=request,
                )
            elif not request and last_seen is not None:
                last_seen = None
                await self.set_state(
                    status="running",
                    running=True,
                    needs_input=False,
                    message="Continuing",
                    pending_request=None,
                )

    async def _poll_progress(self) -> None:
        sent = 0
        while self.agent_task and not self.agent_task.done():
            await asyncio.sleep(0.5)
            if not self.brain:
                continue
            progress = self.brain.step_log
            for event in progress[sent:]:
                pending_request = getattr(self.brain.input_handler, "pending_request", None)
                display_message = progress_message(event, pending_request)
                event_payload = dict(event)
                event_payload["display_message"] = display_message
                await self.broadcast(type="progress", event=event_payload)
                await self.set_state(
                    status="needs_input" if pending_request else "running",
                    running=True,
                    needs_input=bool(pending_request),
                    step=event.get("step"),
                    message=display_message,
                    pending_request=pending_request,
                )
            sent = len(progress)

    async def answer(self, text: str, payload: dict | None = None) -> None:
        if self.brain is None:
            await self.broadcast(type="error", text="no active agent")
            return
        if payload:
            text = json.dumps(payload)
        self.brain.input_handler.provide_input(text)
        await self.broadcast(type="status", text="answer received")
        await self.set_state(
            status="running",
            running=True,
            needs_input=False,
            message="Answer received. Continuing the run.",
            pending_request=None,
        )

    async def cancel(self) -> None:
        if self.agent_task and not self.agent_task.done():
            self.agent_task.cancel()
            await self.broadcast(type="status", text="cancelled")
            await self.set_state(
                status="cancelled",
                running=False,
                needs_input=False,
                message="Cancelled",
                finished_at=now_iso(),
                pending_request=None,
            )


run_manager = RunManager()


class Session:
    """One WebSocket connection = one dashboard client."""

    def __init__(self, ws: WebSocket):
        self.ws = ws

    async def send(self, **payload) -> None:
        await self.ws.send_text(json.dumps(payload))

    async def handle(self) -> None:
        run_manager.attach(self)
        await self.send(type="ready")
        await run_manager.send_snapshot(self)
        while True:
            raw = await self.ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "list_sites":
                await self.send(type="sites", items=run_manager._sites_payload())
            elif mtype == "resolve":
                url = msg.get("url") or ""
                site_id = resolve_from_url(url)
                await self.send(type="resolved", url=url, site=site_id)
            elif mtype == "start":
                await run_manager.start(msg)
            elif mtype == "answer":
                await run_manager.answer(msg.get("text", ""), payload=msg.get("payload"))
            elif mtype == "cancel":
                await run_manager.cancel()
            else:
                await self.send(type="error", text=f"unknown message type: {mtype}")


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^(http://127\.0\.0\.1(:\d+)?|http://localhost(:\d+)?|"
            r"chrome-extension://[a-z]+)$"
        ),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if DASHBOARD_DIR.exists():
        app.mount(
            "/dashboard",
            StaticFiles(directory=DASHBOARD_DIR, html=True),
            name="dashboard",
        )

    @app.get("/")
    async def dashboard_root():
        return RedirectResponse(url="/dashboard/")

    @app.get("/health")
    async def health():
        return {"ok": True, "sites": list_sites()}

    @app.get("/browser/status")
    async def browser_status(cdp_url: str = "http://127.0.0.1:9222"):
        request = BrowserStatusRequest(cdp_url=cdp_url)
        return browser_status_payload(request.cdp_url)

    @app.get("/run/state")
    async def run_state():
        return run_manager.state.snapshot()

    @app.post("/run/start")
    async def run_start(request: RunStartRequest):
        await run_manager.start(request.model_dump())
        return run_manager.state.snapshot()

    @app.post("/run/answer")
    async def run_answer(request: RunAnswerRequest):
        await run_manager.answer(request.text, payload=request.payload)
        return run_manager.state.snapshot()

    @app.post("/run/cancel")
    async def run_cancel():
        await run_manager.cancel()
        return run_manager.state.snapshot()

    @app.post("/browser/launch")
    async def browser_launch(request: BrowserLaunchRequest):
        if request.site not in list_sites():
            return {
                "ok": False,
                "error": f"Unknown site '{request.site}'. Available: {', '.join(list_sites())}",
            }
        if request.chrome_profile not in {"dedicated", "default"}:
            return {
                "ok": False,
                "error": "chrome_profile must be dedicated or default",
            }

        adapter = get_site_adapter(request.site)
        initial_url = request.initial_url or adapter.chat_url or "about:blank"
        try:
            cdp_url = await asyncio.to_thread(
                launch_cdp_chrome,
                ChromeLaunchConfig(
                    cdp_port=request.cdp_port,
                    chrome_profile=request.chrome_profile,
                    chrome_user_data_dir=request.chrome_user_data_dir,
                    initial_url=initial_url,
                    disable_extensions=True,
                    window_width=request.window_width,
                    window_height=request.window_height,
                    window_left=request.window_left,
                    window_top=request.window_top,
                ),
            )
        except Exception as exc:
            logger.exception("browser launch failed")
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        status = browser_status_payload(cdp_url)
        return {
            "ok": True,
            "cdp_url": cdp_url,
            "current_url": status.get("current_url") or initial_url,
            "current_title": status.get("current_title") or "",
            "message": "Chrome is ready. Prepare the visible tab, then start the task.",
        }

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        session = Session(ws)
        try:
            await session.handle()
        except WebSocketDisconnect:
            logger.info("client disconnected")
            run_manager.detach(session)

    _ = TaskStatus
    return app


def browser_status_payload(cdp_url: str) -> dict:
    from urllib.parse import urlparse

    try:
        parsed = urlparse(cdp_url)
        port = parsed.port or 9222
    except ValueError:
        return {
            "ok": False,
            "connected": False,
            "cdp_url": cdp_url,
            "message": "Browser endpoint is invalid.",
        }
    connected = debugger_is_ready(port)
    page_info = debugger_page_info(port) if connected else None
    return {
        "ok": True,
        "connected": connected,
        "cdp_url": f"http://127.0.0.1:{port}",
        "current_url": page_info.get("url") if page_info else None,
        "current_title": page_info.get("title") if page_info else None,
        "message": "Controlled Chrome is connected."
        if connected
        else "Launch the work window before starting.",
    }
