import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.agent.brain import AgentBrain
from src.agent.browser_runtime import (
    ChromeLaunchConfig,
    launch_cdp_chrome,
    supported_chrome_profile_modes,
)
from src.api.auth import get_current_user
from src.api.auth import router as auth_router
from src.models.db import AsyncSessionLocal, init_db
from src.models.task import TaskRecord
from src.models.user import User
from src.sites.registry import get_site_adapter, list_sites
from src.sites.task_templates import get_templates, list_all_templates

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    await init_db()
    yield


app = FastAPI(
    title="Flying Pig AI",
    description="客服上树 — AI customer service agent API",
    version="1.0.2",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# --- In-memory active task brains (TaskStore is now DB) ---
_task_brains: dict[str, AgentBrain] = {}


# --- Request/Response models ---


class HealthResponse(BaseModel):
    status: str
    version: str


class TaskRequest(BaseModel):
    site: str
    task: str
    template: str | None = None
    headless: bool = True
    model: str | None = None
    fallback_model: str | None = None
    cdp_url: str | None = None
    navigate_on_attach: bool = False
    max_steps: int = 100


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: dict | None = None
    pending_question: str | None = None
    progress: list[dict] = Field(default_factory=list)
    created_at: str
    updated_at: str


class UserInputRequest(BaseModel):
    response: str


class BrowserLaunchRequest(BaseModel):
    site: str = "generic"
    cdp_port: int = 9222
    chrome_profile: str = "dedicated"
    chrome_user_data_dir: str | None = None
    initial_url: str | None = None
    dashboard_url: str | None = None
    window_width: int = 1120
    window_height: int = 900
    window_left: int = 560
    window_top: int = 80


class BrowserLaunchResponse(BaseModel):
    cdp_url: str
    message: str


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    required_inputs: list[str]


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="1.0.2")


@app.get("/sites")
async def get_sites():
    return {"sites": list_sites()}


@app.get("/sites/{site}/templates")
async def get_site_templates(site: str):
    templates = get_templates(site)
    return {
        "site": site,
        "templates": [
            TemplateInfo(
                id=t.id,
                name=t.name,
                description=t.description,
                required_inputs=t.required_inputs,
            )
            for t in templates
        ],
    }


@app.get("/templates")
async def get_all_templates():
    all_templates = list_all_templates()
    result = {}
    for site, templates in all_templates.items():
        result[site] = [
            TemplateInfo(
                id=t.id,
                name=t.name,
                description=t.description,
                required_inputs=t.required_inputs,
            )
            for t in templates
        ]
    return result


@app.post("/browser/launch", response_model=BrowserLaunchResponse)
async def launch_browser(
    request: BrowserLaunchRequest,
    current_user: User = Depends(get_current_user),
):
    """Launch a visible Flying Pig work window for supervised dashboard runs."""
    if request.site not in list_sites():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown site '{request.site}'. Available: {', '.join(list_sites())}",
        )
    if request.chrome_profile not in supported_chrome_profile_modes():
        raise HTTPException(
            status_code=400,
            detail="chrome_profile must be dedicated, default, or existing",
        )

    adapter = get_site_adapter(request.site)
    initial_url = request.initial_url or adapter.chat_url or "about:blank"
    cdp_url = await asyncio.to_thread(
        launch_cdp_chrome,
        ChromeLaunchConfig(
            cdp_port=request.cdp_port,
            chrome_profile=request.chrome_profile,
            chrome_user_data_dir=request.chrome_user_data_dir,
            initial_url=initial_url,
            dashboard_url=request.dashboard_url,
            disable_extensions=True,
            window_width=request.window_width,
            window_height=request.window_height,
            window_left=request.window_left,
            window_top=request.window_top,
        ),
    )
    _ = current_user
    return BrowserLaunchResponse(
        cdp_url=cdp_url,
        message="Chrome is ready. Prepare the visible tab, then start the task.",
    )


@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest, current_user: User = Depends(get_current_user)):
    """Create and start a new customer service task."""
    if request.site not in list_sites():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown site '{request.site}'. Available: {', '.join(list_sites())}",
        )

    task_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC).isoformat()

    # Create initial DB record in a short-lived session
    async with AsyncSessionLocal() as session:
        record = TaskRecord(
            id=task_id,
            user_id=current_user.id,
            site=request.site,
            task_prompt=request.task,
            template=request.template,
            status="running",
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        await session.commit()

    # Create brain with API input mode
    brain = AgentBrain(
        site=request.site,
        headless=request.headless,
        input_mode="api",
        model=request.model,
        fallback_model=request.fallback_model,
        cdp_url=request.cdp_url,
        navigate_on_attach=request.navigate_on_attach,
    )
    _task_brains[task_id] = brain

    # Run task in background
    asyncio.create_task(_run_task(task_id, brain, request))

    return TaskResponse(
        task_id=task_id,
        status="running",
        message=f"Task started: {request.task} on {request.site}",
    )


async def _run_task(task_id: str, brain: AgentBrain, request: TaskRequest):
    """Execute the task in background and flush to DB."""
    try:
        result = await brain.execute(
            task=request.task,
            max_steps=request.max_steps,
            template_id=request.template,
        )
        async with AsyncSessionLocal() as session:
            stmt = select(TaskRecord).where(TaskRecord.id == task_id)
            db_res = await session.execute(stmt)
            record = db_res.scalar_one()
            record.status = result.status.value
            record.result_summary = result.summary
            record.outcome_details = result.outcome_details
            record.transcript = result.transcript
            record.transcript_path = result.transcript_path
            record.updated_at = datetime.now(UTC).isoformat()
            await session.commit()
    except Exception as e:
        logger.exception(f"Task {task_id} failed: {e}")
        async with AsyncSessionLocal() as session:
            stmt = select(TaskRecord).where(TaskRecord.id == task_id)
            db_res = await session.execute(stmt)
            record = db_res.scalar_one()
            record.status = "failed"
            record.result_summary = str(e)
            record.updated_at = datetime.now(UTC).isoformat()
            await session.commit()
    finally:
        _task_brains.pop(task_id, None)


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the status of a running or completed task."""
    async with AsyncSessionLocal() as session:
        stmt = select(TaskRecord).where(
            TaskRecord.id == task_id,
            TaskRecord.user_id == current_user.id,
        )
        db_res = await session.execute(stmt)
        record = db_res.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    brain = _task_brains.get(task_id)
    pending = brain.input_handler.pending_question if brain else record.pending_question
    progress = brain.step_log if brain else []

    res_dict = None
    if record.status != "running":
        res_dict = {
            "summary": record.result_summary,
            "outcome_details": record.outcome_details,
            "transcript": record.transcript,
            "transcript_path": record.transcript_path,
        }

    return TaskStatusResponse(
        task_id=record.id,
        status=record.status,
        result=res_dict,
        pending_question=pending,
        progress=progress,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@app.post("/tasks/{task_id}/input")
async def provide_task_input(
    task_id: str,
    request: UserInputRequest,
    current_user: User = Depends(get_current_user),
):
    """Provide user input to a task that's waiting for it."""
    brain = _task_brains.get(task_id)
    if brain is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found or no longer running",
        )

    if not brain.input_handler.pending_question:
        raise HTTPException(
            status_code=400,
            detail="Task is not waiting for input",
        )

    brain.input_handler.provide_input(request.response)
    return {"status": "input_provided", "task_id": task_id}


@app.get("/tasks", tags=["audit"])
async def list_tasks(current_user: User = Depends(get_current_user)):
    """List historical tasks for the user."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(TaskRecord)
            .where(TaskRecord.user_id == current_user.id)
            .order_by(TaskRecord.created_at.desc())
        )
        db_res = await session.execute(stmt)
        records = db_res.scalars().all()

    return {
        "tasks": [
            {
                "id": r.id,
                "site": r.site,
                "template": r.template,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in records
        ]
    }
