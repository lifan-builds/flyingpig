"""WebSocket daemon that connects a frontend (dashboard or CLI) to AgentBrain.

Protocol (JSON per frame, both directions):

  Client -> Daemon:
    {"type": "start", "site": "amex", "template": "negotiate_fee",
     "task": "...", "cdp_url": "http://127.0.0.1:9222",
     "permission_mode": "supervised_browser", "user_authorized": true}
    {"type": "answer", "text": "..."}                  # response to a "question"
    {"type": "huca"}                                    # restart same task in a fresh chat
    {"type": "cancel"}
    {"type": "list_sites"}

  Daemon -> Client:
    {"type": "sites", "items": [...]}
    {"type": "state", "status": "ready_to_start|running|waiting_on_rep|..."}
    {"type": "status", "text": "..."}                  # human-readable progress
    {"type": "progress", "event": {...}}                # step-level agent progress
    {"type": "missing_information|otp_required|manual_login_required|...", ...}
    {"type": "decision_checkpoint", "checkpoint": {...}}
    {"type": "active_human_work", "summary": "..."}
    {"type": "preflight_failed", "failures": [...]}
    {"type": "result_ready", "status": "success|partial|failed|needs_input",
                             "summary": "...", "evidence": {...}}
    {"type": "error", "text": "..."}
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from time import perf_counter

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
    normalize_cdp_url,
    prepare_debugger_page,
    supported_chrome_profile_modes,
)
from src.agent.chrome_devtools_mcp import (
    ChromeDevtoolsMcpError,
    get_default_mcp_session,
    summarize_mcp_error,
)
from src.agent.run_orchestration import build_agent_run_plan
from src.daemon.follow_up_reminders import FollowUpReminderStore
from src.daemon.model_settings import model_settings_payload, save_model_settings
from src.daemon.preflight import preflight_check, task_with_success_criteria
from src.daemon.run_session import (
    RunEventType,
    RunStateStore,
    RunStatus,
    normalize_attention_request,
    now_iso,
    progress_event_type,
    progress_message,
    protocol_event_for_request,
    request_message,
    result_payload,
    run_status_for_attention,
    timing_span,
)
from src.sites.registry import get_site_adapter, list_sites, resolve_from_url
from src.sites.task_templates import get_templates

logger = logging.getLogger(__name__)
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
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


class BrowserAttachRequest(BaseModel):
    cdp_url: str = "http://127.0.0.1:9222"
    initial_url: str | None = None
    prepare_page: bool = False


class BrowserMcpSelectRequest(BaseModel):
    page_index: int | None = None
    page_id: str | None = None
    url: str | None = None


class RunStartRequest(BaseModel):
    site: str | None = "generic"
    url: str = ""
    template: str | None = None
    task: str
    cdp_url: str | None = None
    target_url: str | None = None
    browser_backend: str = "browser_use"
    mcp_page: dict | None = None
    model: str | None = None
    fallback_model: str | None = None
    max_steps: int = 80
    navigate_on_attach: bool = False
    success_criteria: str | None = None
    permission_mode: str = "supervised_browser"
    user_authorized: bool = False
    evidence_capture: bool = True
    login_expectation: str | None = None
    irreversible_actions_require_checkpoint: bool = True
    authorization: dict | None = None


class RunAnswerRequest(BaseModel):
    text: str = ""
    payload: dict | None = None


class RunOutcomeRequest(BaseModel):
    outcome: str


class ModelSettingsRequest(BaseModel):
    default_model: str | None = None
    provider: str | None = None
    api_key: str | None = None
    clear_key: bool = False


class FollowUpReminderRequest(BaseModel):
    title: str
    message: str
    due_at: datetime
    source: dict | None = None


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
        self.current_run_request: dict | None = None
        self.timing_spans: list[dict] = []
        self.huca_attempts = 0
        self._user_wait_started_at: float | None = None
        self._rep_wait_started_at: float | None = None

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

    async def add_timing_span(self, span: dict) -> None:
        event = dict(span)
        event["type"] = "timing_span"
        self.timing_spans.append(event)
        await self.broadcast(**event)

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
            await self._start_locked(msg)

    async def _start_locked(self, msg: dict, *, huca: bool = False) -> None:
        if self.agent_task and not self.agent_task.done():
            await self.broadcast(type="error", text="agent already running")
            return

        await self.set_state(
            status=RunStatus.PREPARING.value,
            running=False,
            needs_input=False,
            message="Checking task scope, permissions, login expectations, and evidence settings.",
            preflight_failures=[],
            timing_spans=[],
        )

        url = msg.get("url") or ""
        requested_site = msg.get("site")
        site = resolve_from_url(url) if requested_site in (None, "", "auto") else requested_site
        if not site:
            site = None
        self.timing_spans = []
        if huca:
            self.huca_attempts += 1
        else:
            self.huca_attempts = 0
        self._user_wait_started_at = None
        self._rep_wait_started_at = None

        preflight_started_at = perf_counter()
        preflight = preflight_check(msg, site=site)
        await self.add_timing_span(
            timing_span(
                "preflight",
                "Pre-flight safety gate",
                duration_ms=(perf_counter() - preflight_started_at) * 1000,
                status="ok" if preflight.ok else "blocked",
                metadata={"failure_count": len(preflight.failures)},
            )
        )
        if not preflight.ok:
            await self.broadcast(
                type="preflight_failed",
                failures=preflight.failures,
                text="Pre-flight check failed.",
            )
            await self.set_state(
                status=RunStatus.READY_TO_START.value,
                running=False,
                needs_input=False,
                message="Pre-flight blocked the run. Fix the listed items before starting.",
                site=None,
                preflight_failures=preflight.failures,
                timing_spans=list(self.timing_spans),
            )
            return

        user_task = msg.get("task") or ""
        task_brief = task_with_success_criteria(user_task, msg.get("success_criteria"))
        run_plan = build_agent_run_plan(
            msg,
            site=site,
            task_brief=task_brief,
            huca=huca,
        )

        construction_started_at = perf_counter()
        self.brain = AgentBrain(**run_plan.agent_kwargs())
        await self.add_timing_span(
            timing_span(
                "agent_construction",
                "AgentBrain construction",
                duration_ms=(perf_counter() - construction_started_at) * 1000,
            )
        )
        started_at = now_iso()
        self.current_run_request = {
            **msg,
            "site": site,
            "url": url,
            "template": run_plan.template_id,
            "task": user_task,
            "success_criteria": msg.get("success_criteria"),
            "cdp_url": run_plan.cdp_url,
            "target_url": run_plan.target_url,
        }
        status_text = f"using adapter: {site}"
        if huca:
            status_text = f"HUCA restart: using adapter: {site}"
        await self.broadcast(type="status", text=status_text)
        message = f"Starting agent for {site}"
        if huca:
            message = f"Restarting fresh chat for {site}"
        await self.set_state(
            status=RunStatus.RUNNING.value,
            running=True,
            needs_input=False,
            site=site,
            message=message,
            step=None,
            started_at=started_at,
            finished_at=None,
            transcript=None,
            result=None,
            pending_request=None,
            permission_mode=run_plan.permission_mode,
            preflight_failures=[],
            timing_spans=list(self.timing_spans),
        )
        self.agent_task = asyncio.create_task(self._run_agent(**run_plan.execute_kwargs()))
        self.questions_task = asyncio.create_task(self._poll_questions())
        self.progress_task = asyncio.create_task(self._poll_progress())

    async def huca(self, msg: dict) -> None:
        async with self.lock:
            previous_request = dict(self.current_run_request or {})
            restart_request = {
                **previous_request,
                **{key: value for key, value in msg.items() if value not in (None, "")},
            }
            if not restart_request.get("task"):
                await self.broadcast(type="error", text="no task available for HUCA restart")
                return

            if self.agent_task and not self.agent_task.done():
                stopped = await self._cancel_active_run(
                    status_message="HUCA restart requested. Stopping current chat."
                )
                if not stopped:
                    await self.broadcast(
                        type="error",
                        text="could not stop the current run for HUCA restart",
                    )
                    return

            await self._start_locked(restart_request, huca=True)

    async def _run_agent(self, *, task: str, template_id: str | None, max_steps: int) -> None:
        try:
            assert self.brain is not None
            result = await self.brain.execute(
                task=task, max_steps=max_steps, template_id=template_id
            )
            await self._finish_open_wait_spans()
            result.timing_spans = self._merged_timing_spans(
                self.timing_spans,
                result.timing_spans,
            )
            self.timing_spans = list(result.timing_spans)
            result.outcome_details = {
                **(result.outcome_details or {}),
                "site": self.current_run_request.get("site") if self.current_run_request else None,
                "site_profile": self.current_run_request.get("site")
                if self.current_run_request
                else None,
                "template": self.current_run_request.get("template")
                if self.current_run_request
                else None,
                "huca_attempts": self.huca_attempts,
            }
            payload = result_payload(result)
            await self.broadcast(**payload)
            final_status = (
                RunStatus.FAILED.value
                if payload["status"] == "failed"
                else RunStatus.COMPLETED.value
            )
            await self.set_state(
                status=final_status,
                running=False,
                needs_input=False,
                message=result.summary,
                step=result.steps_taken,
                finished_at=now_iso(),
                transcript=payload["transcript"],
                result=payload,
                pending_request=None,
                timing_spans=list(result.timing_spans),
            )
        except asyncio.CancelledError:
            await self.set_state(
                status=RunStatus.CANCELLED.value,
                running=False,
                needs_input=False,
                message="Cancelled",
                finished_at=now_iso(),
                pending_request=None,
                timing_spans=list(self.timing_spans),
            )
            raise
        except Exception as e:
            logger.exception("agent run failed")
            await self.broadcast(type="error", text=f"{type(e).__name__}: {e}")
            await self.set_state(
                status=RunStatus.FAILED.value,
                running=False,
                needs_input=False,
                message=f"{type(e).__name__}: {e}",
                finished_at=now_iso(),
                pending_request=None,
                timing_spans=list(self.timing_spans),
            )

    async def _poll_questions(self) -> None:
        last_seen: str | None = None
        while self.agent_task and not self.agent_task.done():
            await asyncio.sleep(0.3)
            if not self.agent_task or self.agent_task.done():
                break
            if not self.brain:
                continue
            request = getattr(self.brain.input_handler, "pending_request", None)
            request_key = json.dumps(request, sort_keys=True) if request else None
            if request and request_key != last_seen:
                last_seen = request_key
                pending_request = protocol_event_for_request(request)
                await self.broadcast(**pending_request)
                self._user_wait_started_at = perf_counter()
                await self.set_state(
                    status=run_status_for_attention(pending_request).value,
                    running=True,
                    needs_input=True,
                    message=request_message(pending_request),
                    pending_request=pending_request,
                )
            elif not request and last_seen is not None:
                last_seen = None
                await self._finish_user_wait_span()
                await self.set_state(
                    status=RunStatus.RUNNING.value,
                    running=True,
                    needs_input=False,
                    message="Continuing",
                    pending_request=None,
                )

    async def _poll_progress(self) -> None:
        sent = 0
        while self.agent_task and not self.agent_task.done():
            await asyncio.sleep(0.5)
            if not self.agent_task or self.agent_task.done():
                break
            if not self.brain:
                continue
            progress = self.brain.step_log
            for event in progress[sent:]:
                if event.get("type") == "timing_span":
                    event_payload = dict(event)
                    self.timing_spans = self._merged_timing_spans(
                        self.timing_spans,
                        [event_payload],
                    )
                    await self.broadcast(**event_payload)
                    await self.set_state(timing_spans=list(self.timing_spans))
                    continue
                pending_request = getattr(self.brain.input_handler, "pending_request", None)
                normalized_request = normalize_attention_request(pending_request)
                display_message = progress_message(event, normalized_request)
                event_payload = dict(event)
                event_payload["display_message"] = display_message
                lifecycle_type = progress_event_type(event_payload)
                await self.broadcast(type="progress", event=event_payload)
                if lifecycle_type == RunEventType.ACTIVE_HUMAN_WORK:
                    if self._rep_wait_started_at is None:
                        self._rep_wait_started_at = perf_counter()
                    await self.broadcast(
                        type=RunEventType.ACTIVE_HUMAN_WORK.value,
                        summary=display_message,
                        step=event.get("step"),
                    )
                status = (
                    RunStatus.WAITING_ON_REP
                    if lifecycle_type == RunEventType.ACTIVE_HUMAN_WORK
                    else run_status_for_attention(normalized_request)
                    if normalized_request
                    else RunStatus.RUNNING
                )
                if lifecycle_type != RunEventType.ACTIVE_HUMAN_WORK:
                    await self._finish_rep_wait_span()
                await self.set_state(
                    status=status.value,
                    running=True,
                    needs_input=bool(normalized_request),
                    step=event.get("step"),
                    message=display_message,
                    pending_request=normalized_request,
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
            status=RunStatus.RUNNING.value,
            running=True,
            needs_input=False,
            message="Answer received. Continuing the run.",
            pending_request=None,
        )
        await self._finish_user_wait_span()

    async def cancel(self) -> None:
        async with self.lock:
            await self._cancel_active_run(status_message="cancelled")

    async def mark_outcome(self, outcome: str) -> dict:
        allowed = {"solved", "partial", "failed"}
        if outcome not in allowed:
            options = ", ".join(sorted(allowed))
            return {"ok": False, "error": f"outcome must be one of: {options}"}
        snapshot = self.state.snapshot()
        result = dict(snapshot.get("result") or {})
        if not result:
            return {"ok": False, "error": "no completed result to mark"}
        scorecard = dict(result.get("scorecard") or {})
        scorecard["user_confirmed_outcome"] = outcome
        result["scorecard"] = scorecard
        await self.set_state(result=result)
        await self.broadcast(type="scorecard_updated", scorecard=scorecard)
        return {"ok": True, "scorecard": scorecard}

    async def _cancel_active_run(self, *, status_message: str) -> bool:
        if self.agent_task and not self.agent_task.done():
            await self._cancel_observer_tasks()
            self.agent_task.cancel()
            try:
                await asyncio.wait_for(self.agent_task, timeout=15)
            except asyncio.CancelledError:
                pass
            except TimeoutError:
                logger.warning("timed out waiting for agent task cancellation")
                return False
            await self.broadcast(type="status", text=status_message)
            await self.set_state(
                status=RunStatus.CANCELLED.value,
                running=False,
                needs_input=False,
                message="Cancelled" if status_message == "cancelled" else status_message,
                finished_at=now_iso(),
                pending_request=None,
                timing_spans=list(self.timing_spans),
            )
        return True

    async def _finish_open_wait_spans(self) -> None:
        await self._finish_user_wait_span()
        await self._finish_rep_wait_span()

    async def _finish_user_wait_span(self) -> None:
        if self._user_wait_started_at is None:
            return
        started_at = self._user_wait_started_at
        self._user_wait_started_at = None
        await self.add_timing_span(
            timing_span(
                "user_wait",
                "Waiting on user",
                duration_ms=(perf_counter() - started_at) * 1000,
            )
        )

    async def _finish_rep_wait_span(self) -> None:
        if self._rep_wait_started_at is None:
            return
        started_at = self._rep_wait_started_at
        self._rep_wait_started_at = None
        await self.add_timing_span(
            timing_span(
                "representative_wait",
                "Waiting on representative",
                duration_ms=(perf_counter() - started_at) * 1000,
            )
        )

    def _merged_timing_spans(self, *span_groups: list[dict]) -> list[dict]:
        merged: list[dict] = []
        seen: set[tuple] = set()
        for spans in span_groups:
            for span in spans:
                key = (
                    span.get("name"),
                    span.get("timestamp"),
                    span.get("duration_ms"),
                    json.dumps(span.get("metadata") or {}, sort_keys=True),
                )
                if key in seen:
                    continue
                seen.add(key)
                event = dict(span)
                event["type"] = "timing_span"
                merged.append(event)
        return merged

    async def _cancel_observer_tasks(self) -> None:
        tasks = [task for task in (self.questions_task, self.progress_task) if task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.questions_task = None
        self.progress_task = None


run_manager = RunManager()


def chrome_mcp_session():
    """Return the helper-owned Chrome DevTools MCP session."""
    return get_default_mcp_session()


def browser_mcp_connect_payload() -> dict:
    """Connect to Chrome DevTools MCP and list existing Chrome pages."""
    try:
        pages = chrome_mcp_session().connect()
    except (ChromeDevtoolsMcpError, OSError) as exc:
        return {
            "ok": False,
            "connected": False,
            "pages": [],
            "message": summarize_mcp_error(exc),
        }

    return {
        "ok": True,
        "connected": True,
        "pages": pages,
        "message": (
            "Chrome DevTools MCP connected. Select the existing Chrome tab "
            "Flying Pig may supervise."
        ),
    }


def browser_mcp_select_payload(request: BrowserMcpSelectRequest) -> dict:
    """Select and snapshot a user-authorized existing Chrome page through MCP."""
    try:
        session = chrome_mcp_session()
        pages = session.list_pages()
        page = _select_mcp_page(
            pages,
            page_index=request.page_index,
            page_id=request.page_id,
            url=request.url,
        )
        if page is None:
            return {
                "ok": False,
                "connected": True,
                "message": (
                    "Selected Chrome tab was not found. Refresh the tab list and try again."
                ),
                "pages": pages,
            }
        snapshot = session.select_page(page)
    except (ChromeDevtoolsMcpError, OSError) as exc:
        return {
            "ok": False,
            "connected": False,
            "message": summarize_mcp_error(exc),
        }

    selected_page = {
        **page,
        "snapshot_available": bool(snapshot.get("snapshot_text") or snapshot.get("snapshot")),
    }
    cdp_url = page.get("cdp_url")
    return {
        "ok": True,
        "connected": True,
        "page": selected_page,
        "cdp_url": cdp_url,
        "current_url": page.get("url") or "",
        "current_title": page.get("title") or "",
        "browser_backend": "mcp",
        "browser_ready": True,
        "message": "Existing Chrome tab selected and ready for MCP control.",
    }


def _select_mcp_page(
    pages: list[dict],
    *,
    page_index: int | None = None,
    page_id: str | None = None,
    url: str | None = None,
) -> dict | None:
    if page_id:
        for page in pages:
            if str(page.get("id") or "") == page_id:
                return page
    if url:
        for page in pages:
            if page.get("url") == url:
                return page
    if page_index is not None:
        for page in pages:
            if page.get("index") == page_index:
                return page
    return pages[0] if pages else None


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
            elif mtype == "huca":
                await run_manager.huca(msg)
            elif mtype == "cancel":
                await run_manager.cancel()
            else:
                await self.send(type="error", text=f"unknown message type: {mtype}")


def create_app(reminder_store: FollowUpReminderStore | None = None) -> FastAPI:
    store = reminder_store or FollowUpReminderStore()

    async def reminder_loop() -> None:
        while True:
            if run_manager.sessions:
                for reminder in store.claim_due():
                    await run_manager.broadcast(
                        type="follow_up_reminder_due",
                        reminder=reminder.model_dump(mode="json"),
                    )
            await asyncio.sleep(5)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.follow_up_reminder_store = store
        task = asyncio.create_task(reminder_loop())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    app = FastAPI(lifespan=lifespan)
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

    @app.get("/model/settings")
    async def model_settings():
        return model_settings_payload()

    @app.post("/model/settings")
    async def model_settings_update(request: ModelSettingsRequest):
        try:
            return save_model_settings(**request.model_dump())
        except ValueError as exc:
            return {**model_settings_payload(), "ok": False, "error": str(exc)}

    @app.post("/run/start")
    async def run_start(request: RunStartRequest):
        await run_manager.start(request.model_dump())
        return run_manager.state.snapshot()

    @app.post("/run/answer")
    async def run_answer(request: RunAnswerRequest):
        await run_manager.answer(request.text, payload=request.payload)
        return run_manager.state.snapshot()

    @app.post("/run/outcome")
    async def run_outcome(request: RunOutcomeRequest):
        return await run_manager.mark_outcome(request.outcome)

    @app.get("/follow-up-reminders")
    async def follow_up_reminders():
        return {
            "items": [item.model_dump(mode="json") for item in store.list()],
        }

    @app.post("/follow-up-reminders")
    async def follow_up_reminder_create(request: FollowUpReminderRequest):
        reminder = store.create(**request.model_dump())
        return {"ok": True, "reminder": reminder.model_dump(mode="json")}

    @app.delete("/follow-up-reminders/{reminder_id}")
    async def follow_up_reminder_cancel(reminder_id: str):
        reminder = store.cancel(reminder_id)
        return {
            "ok": reminder is not None,
            "reminder": reminder.model_dump(mode="json") if reminder else None,
        }

    @app.post("/run/cancel")
    async def run_cancel():
        await run_manager.cancel()
        return run_manager.state.snapshot()

    @app.post("/run/huca")
    async def run_huca(request: RunStartRequest):
        await run_manager.huca(request.model_dump())
        return run_manager.state.snapshot()

    @app.post("/browser/launch")
    async def browser_launch(request: BrowserLaunchRequest):
        if request.site not in list_sites():
            return {
                "ok": False,
                "error": f"Unknown site '{request.site}'. Available: {', '.join(list_sites())}",
            }
        if request.chrome_profile not in supported_chrome_profile_modes():
            return {
                "ok": False,
                "error": (
                    "chrome_profile must be dedicated, default, or existing. "
                    "The literal existing default profile may be blocked by Chrome unless "
                    "you provide a non-default chrome_user_data_dir."
                ),
            }

        adapter = get_site_adapter(request.site)
        initial_url = request.initial_url or adapter.chat_url or "about:blank"
        try:
            launch_started_at = perf_counter()
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
            launch_span = timing_span(
                "launch",
                "Work window launch",
                duration_ms=(perf_counter() - launch_started_at) * 1000,
            )
            await run_manager.add_timing_span(launch_span)
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
            "timing_span": launch_span,
        }

    @app.post("/browser/attach")
    async def browser_attach(request: BrowserAttachRequest):
        try:
            cdp_url = normalize_cdp_url(request.cdp_url)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        if not debugger_is_ready(cdp_url=cdp_url):
            return {
                "ok": False,
                "error": (
                    f"Could not connect to Chrome at {cdp_url}. Start Chrome with "
                    "--remote-debugging-port=<port>, then enter that endpoint here. "
                    "If using Chrome DevTools MCP auto-connect, open "
                    "chrome://inspect/#remote-debugging and allow remote debugging."
                ),
                "cdp_url": cdp_url,
            }

        if request.prepare_page:
            prepare_debugger_page(
                cdp_url=cdp_url,
                target_url=request.initial_url or "about:blank",
            )

        status = browser_status_payload(cdp_url)
        return {
            "ok": True,
            "cdp_url": cdp_url,
            "current_url": status.get("current_url") or request.initial_url or "",
            "current_title": status.get("current_title") or "",
            "message": "Existing Chrome connected. Prepare the visible tab, then start the task.",
        }

    @app.post("/browser/mcp/connect")
    async def browser_mcp_connect():
        return await asyncio.to_thread(browser_mcp_connect_payload)

    @app.get("/browser/mcp/pages")
    async def browser_mcp_pages():
        return await asyncio.to_thread(browser_mcp_connect_payload)

    @app.post("/browser/mcp/select")
    async def browser_mcp_select(request: BrowserMcpSelectRequest):
        return await asyncio.to_thread(browser_mcp_select_payload, request)

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
    try:
        normalized_url = normalize_cdp_url(cdp_url)
    except ValueError:
        return {
            "ok": False,
            "connected": False,
            "cdp_url": cdp_url,
            "message": "Browser endpoint is invalid.",
        }

    connected = debugger_is_ready(cdp_url=normalized_url)
    page_info = debugger_page_info(cdp_url=normalized_url) if connected else None
    return {
        "ok": True,
        "connected": connected,
        "cdp_url": normalized_url,
        "current_url": page_info.get("url") if page_info else None,
        "current_title": page_info.get("title") if page_info else None,
        "message": "Controlled Chrome is connected."
        if connected
        else "Launch the work window before starting.",
    }
