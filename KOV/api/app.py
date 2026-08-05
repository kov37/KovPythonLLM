"""Local-only FastAPI control and observability surface."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from KOV.api.auth import LocalTokenAuth
from KOV.api.projections import DashboardProjection
from KOV.contracts.actions import ViewFileAction
from KOV.contracts.common import StrictModel
from KOV.control.stop import StopController
from KOV.models.chat_gateway import ADKChatGateway, ChatReply
from KOV.research.client import PublicResearchClient
from KOV.storage.ledger import EventLedger
from KOV.tools.atomic import AtomicWorkspaceTools
from KOV.workspaces.registry import WorkspaceRegistry


class ControlRequest(StrictModel):
    reason: str = Field(min_length=3, max_length=500)


class ChatRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    evidence: str = Field(default="", max_length=16_000)


class FileViewRequest(StrictModel):
    path: str = Field(min_length=1, max_length=4_096)
    line_start: int = Field(default=1, ge=1)
    line_end: int = Field(default=100, ge=1)


class WebRequest(StrictModel):
    url: str = Field(min_length=12, max_length=2_048)
    objective: str = Field(min_length=3, max_length=500)


def create_app(state_root: Path | None = None) -> FastAPI:
    project = Path(__file__).resolve().parents[2]
    state = state_root or project / ".kov-state"
    ledger = EventLedger(state / "ledger.sqlite3")
    ledger.initialize()
    stop = StopController(state / "control")
    stop.initialize()
    auth = LocalTokenAuth(state / "control" / "operator.token")
    auth.initialize()
    projection = DashboardProjection(ledger)
    workspace_tools = AtomicWorkspaceTools(WorkspaceRegistry.default())
    app = FastAPI(title="KOV Control Plane", version="0.1.0", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def localhost_only(request: Request, call_next):
        host = request.client.host if request.client else ""
        if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            raise HTTPException(status_code=403, detail="KOV API is localhost-only")
        return await call_next(request)

    def authorize(authorization: str | None = Header(default=None)) -> None:
        if not auth.verify(authorization):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid local operator token required",
            )

    @app.get("/api/overview", dependencies=[Depends(authorize)])
    def overview() -> dict[str, object]:
        return projection.overview()

    @app.get("/api/timeline", dependencies=[Depends(authorize)])
    def timeline(limit: int = 100) -> list[dict[str, object]]:
        return projection.timeline(max(1, min(limit, 500)))

    @app.get("/api/control", dependencies=[Depends(authorize)])
    def control_status() -> dict[str, bool]:
        current = stop.status()
        return {"paused": current.paused, "emergencyStopped": current.emergency_stopped}

    @app.post("/api/control/pause", dependencies=[Depends(authorize)])
    def pause(body: ControlRequest) -> dict[str, bool]:
        stop.pause(body.reason)
        return {"paused": True}

    @app.post("/api/control/emergency-stop", dependencies=[Depends(authorize)])
    def emergency_stop(body: ControlRequest) -> dict[str, bool]:
        stop.emergency_stop(body.reason)
        return {"emergencyStopped": True}

    @app.post("/api/control/resume", dependencies=[Depends(authorize)])
    def resume() -> dict[str, bool]:
        stop.resume(locally_authorized=True)
        return {"paused": False}

    @app.post("/api/assist/chat", dependencies=[Depends(authorize)])
    async def chat(body: ChatRequest) -> ChatReply:
        # Raw prompts are intentionally not written to the ledger.
        return await ADKChatGateway().answer(body.prompt, body.evidence)

    @app.post("/api/assist/file", dependencies=[Depends(authorize)])
    def file_assist(body: FileViewRequest) -> dict[str, object]:
        view = workspace_tools.view_file(
            ViewFileAction(
                workspace="research_tutor",
                path=body.path,
                line_start=body.line_start,
                line_end=min(body.line_end, body.line_start + 99),
            )
        )
        return {
            "path": view.path,
            "content": view.content,
            "digest": view.digest,
            "totalLines": view.total_lines,
        }

    @app.post("/api/assist/web", dependencies=[Depends(authorize)])
    def web_assist(body: WebRequest) -> dict[str, object]:
        result = PublicResearchClient().fetch(body.url, objective=body.objective)
        return {
            "content": result.text,
            "compressed": result.compressed,
            "hiddenLines": result.hidden_lines,
            "redacted": result.redacted,
        }

    dashboard = project / "dashboard" / "dist"
    if dashboard.is_dir():
        app.mount("/assets", StaticFiles(directory=dashboard / "assets"), name="assets")

        @app.get("/{path:path}")
        def frontend(path: str) -> FileResponse:
            del path
            return FileResponse(dashboard / "index.html")

    return app
