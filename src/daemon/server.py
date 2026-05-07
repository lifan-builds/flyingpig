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
    {"type": "result", "status": "success|partial|failed|needs_input",
                       "summary": "...", "steps": N, "duration": S}
    {"type": "error", "text": "..."}
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.agent.brain import AgentBrain, TaskStatus
from src.sites.registry import list_sites, resolve_from_url
from src.sites.task_templates import get_templates

logger = logging.getLogger(__name__)


class RunManager:
    """Owns the active agent run independently of side-panel connections."""

    def __init__(self):
        self.brain: AgentBrain | None = None
        self.agent_task: asyncio.Task | None = None
        self.progress_task: asyncio.Task | None = None
        self.questions_task: asyncio.Task | None = None
        self.sessions: set[Session] = set()
        self.lock = asyncio.Lock()
        self.state: dict = {
            "type": "state",
            "status": "idle",
            "running": False,
            "needs_input": False,
            "site": None,
            "message": "Idle",
            "step": None,
            "updated_at": None,
            "started_at": None,
            "finished_at": None,
            "transcript": None,
            "result": None,
        }

    def attach(self, session: Session) -> None:
        self.sessions.add(session)

    def detach(self, session: Session) -> None:
        self.sessions.discard(session)

    async def send_snapshot(self, session: Session) -> None:
        await session.send(**self.state)

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
        self.state.update(changes)
        self.state["type"] = "state"
        self.state["updated_at"] = datetime.now(UTC).isoformat()
        await self.broadcast(**self.state)

    def _sites_payload(self) -> list[dict]:
        out = []
        for site in list_sites():
            templates = get_templates(site)
            out.append({
                "id": site,
                "templates": [
                    {"id": t.id, "label": t.name, "description": t.description}
                    for t in templates
                ],
            })
        return out

    async def start(self, msg: dict) -> None:
        async with self.lock:
            if self.agent_task and not self.agent_task.done():
                await self.broadcast(type="error", text="agent already running")
                return

            url = msg.get("url") or ""
            requested_site = msg.get("site")
            site = (
                resolve_from_url(url)
                if requested_site in (None, "", "auto")
                else requested_site
            )
            if not site:
                await self.broadcast(
                    type="error",
                    text="Could not detect the current site. Open a supported site tab first.",
                )
                await self.set_state(
                    status="idle",
                    running=False,
                    needs_input=False,
                    message="Open a supported site tab first.",
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
            started_at = datetime.now(UTC).isoformat()
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
            status = str(result.status).split(".")[-1].lower()
            payload = {
                "type": "result",
                "status": status,
                "summary": result.summary,
                "steps": result.steps_taken,
                "duration": result.duration_seconds,
                "transcript": str(result.transcript_path) if result.transcript_path else None,
            }
            await self.broadcast(**payload)
            await self.set_state(
                status=status,
                running=False,
                needs_input=False,
                message=result.summary,
                step=result.steps_taken,
                finished_at=datetime.now(UTC).isoformat(),
                transcript=payload["transcript"],
                result=payload,
            )
        except asyncio.CancelledError:
            await self.set_state(
                status="cancelled",
                running=False,
                needs_input=False,
                message="Cancelled",
                finished_at=datetime.now(UTC).isoformat(),
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
                finished_at=datetime.now(UTC).isoformat(),
            )

    async def _poll_questions(self) -> None:
        last_seen: str | None = None
        while self.agent_task and not self.agent_task.done():
            await asyncio.sleep(0.3)
            if not self.brain:
                continue
            q = self.brain.input_handler.pending_question
            if q and q != last_seen:
                last_seen = q
                await self.broadcast(type="question", question=q, reason="agent needs input")
                await self.set_state(
                    status="needs_input",
                    running=True,
                    needs_input=True,
                    message=q,
                )
            elif not q and last_seen is not None:
                last_seen = None
                await self.set_state(
                    status="running",
                    running=True,
                    needs_input=False,
                    message="Continuing",
                )

    async def _poll_progress(self) -> None:
        sent = 0
        while self.agent_task and not self.agent_task.done():
            await asyncio.sleep(0.5)
            if not self.brain:
                continue
            progress = self.brain.step_log
            for event in progress[sent:]:
                await self.broadcast(type="progress", event=event)
                await self.set_state(
                    status="running",
                    running=True,
                    needs_input=False,
                    step=event.get("step"),
                    message=(
                        event.get("message")
                        or event.get("goal")
                        or event.get("thought")
                        or "Working"
                    ),
                )
            sent = len(progress)

    async def answer(self, text: str) -> None:
        if self.brain is None:
            await self.broadcast(type="error", text="no active agent")
            return
        self.brain.input_handler.provide_input(text)
        await self.broadcast(type="status", text="answer received")
        await self.set_state(
            status="running",
            running=True,
            needs_input=False,
            message="Answer received",
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
                finished_at=datetime.now(UTC).isoformat(),
            )


run_manager = RunManager()


class Session:
    """One WebSocket connection = one side-panel client."""

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
                await run_manager.answer(msg.get("text", ""))
            elif mtype == "cancel":
                await run_manager.cancel()
            else:
                await self.send(type="error", text=f"unknown message type: {mtype}")


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"ok": True, "sites": list_sites()}

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
