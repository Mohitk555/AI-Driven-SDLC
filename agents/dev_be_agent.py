"""Backend Developer Agent — generates FastAPI code from architecture specs."""

from __future__ import annotations

import logging
import re
import textwrap
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DevBackendAgent(BaseAgent):
    """Generates FastAPI backend code based on architecture and requirements.

    Reads ``memory/architecture.md`` for API contracts and DB schemas,
    then produces endpoint, model, and service code under ``/backend/``.
    Creates branches and PRs via GitHub tool-calls.
    """

    agent_id: str = "dev_be_agent"
    role: str = "Backend Developer"
    permissions: list[str] = [
        "github.create_branch",
        "github.push_code",
        "github.create_pr",
        "jira.update_ticket",
    ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Generate backend code artifacts and return tool-calls for Git ops."""
        try:
            self.load_constitution()

            architecture = self.read_memory("architecture.md")
            if not architecture:
                return self._fail(
                    "No architecture document found. Run the Tech Lead Agent first."
                )

            components = self._parse_components(architecture)
            endpoints = self._parse_endpoints(architecture)

            generated_files = self._generate_code(components, endpoints)

            ticket_id = context.get("ticket_id")
            ticket_segment = ticket_id or "no-ticket"
            branch_name = f"feature/{ticket_segment}-backend-implementation"
            base_branch = self._github_base_branch()

            tool_calls: list[ToolCall] = [
                self.create_tool_call(
                    "github.create_branch",
                    {
                        "branch_name": branch_name,
                        "base_ref": base_branch,
                    },
                ),
                self.create_tool_call(
                    "github.push_code",
                    {
                        "branch": branch_name,
                        "files": generated_files,
                        "commit_message": f"feat(backend): add API endpoints for {ticket_segment}",
                    },
                ),
                self.create_tool_call(
                    "github.create_pr",
                    {
                        "repo": "insure-os",
                        "title": f"[{ticket_segment}] Backend API implementation",
                        "body": (
                            f"## Changes\n"
                            f"- Generated {len(generated_files)} backend files\n"
                            f"- API endpoints for {len(endpoints)} routes\n"
                            f"- Pydantic models and service layer\n\n"
                            f"## Testing\n"
                            f"- [ ] Run `pytest`\n"
                            f"- [ ] Verify endpoints via Swagger UI"
                        ),
                        "head": branch_name,
                        "base": base_branch,
                    },
                ),
            ]

            if ticket_id:
                tool_calls.append(
                    self.create_tool_call(
                        "jira.update_ticket",
                        {
                            "ticket_key": ticket_id,
                            "fields": {"status": {"name": "In Review"}},
                        },
                    )
                )

            output = (
                f"Generated {len(generated_files)} backend files covering "
                f"{len(endpoints)} API endpoints. Branch: {branch_name}."
            )
            return self._ok(
                output=output,
                tool_calls=tool_calls,
                metadata={
                    "branch": branch_name,
                    "files_generated": list(generated_files.keys()),
                    "endpoint_count": len(endpoints),
                },
            )

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_components(self, architecture: str) -> list[str]:
        """Extract component names from the architecture document."""
        matches = re.findall(r"\|\s*([A-Z][\w\s]+?Service)\s*\|", architecture)
        return list(dict.fromkeys(matches))  # deduplicate, preserve order

    def _parse_endpoints(self, architecture: str) -> list[dict[str, str]]:
        """Extract API endpoints from the architecture document."""
        pattern = r"\|\s*(GET|POST|PUT|DELETE|PATCH)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\|"
        endpoints: list[dict[str, str]] = []
        for method, path, summary in re.findall(pattern, architecture):
            endpoints.append({
                "method": method.strip(),
                "path": path.strip(),
                "summary": summary.strip(),
            })
        return endpoints

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    def _generate_code(
        self,
        components: list[str],
        endpoints: list[dict[str, str]],
    ) -> dict[str, str]:
        """Generate FastAPI application files.

        Returns a dict of ``{filepath: content}`` for use in the
        ``github.push_code`` tool-call.
        """
        files: dict[str, str] = {}

        # main.py
        files["backend/main.py"] = self._gen_main(components)

        # Per-component modules
        for comp in components:
            module = comp.lower().replace(" service", "").replace(" ", "_")
            files[f"backend/routers/{module}.py"] = self._gen_router(module, endpoints)
            files[f"backend/models/{module}.py"] = self._gen_model(module)
            files[f"backend/services/{module}.py"] = self._gen_service(module)

        # Package inits
        for subdir in ("routers", "models", "services"):
            files[f"backend/{subdir}/__init__.py"] = ""

        # Config and deps
        files["backend/config.py"] = self._gen_config()
        files["backend/deps.py"] = self._gen_deps()

        return files

    # ------------------------------------------------------------------
    # Template generators
    # ------------------------------------------------------------------

    def _gen_main(self, components: list[str]) -> str:
        imports: list[str] = []
        includes: list[str] = []
        for comp in components:
            module = comp.lower().replace(" service", "").replace(" ", "_")
            imports.append(f"from backend.routers.{module} import router as {module}_router")
            includes.append(f'app.include_router({module}_router, prefix="/api/v1/{module}s", tags=["{comp}"])')

        return textwrap.dedent(f'''\
            """FastAPI application entry-point — InsureOS backend."""

            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            {chr(10).join(imports)}

            app = FastAPI(
                title="InsureOS API",
                version="0.1.0",
                docs_url="/api/docs",
                redoc_url="/api/redoc",
            )

            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # tighten per environment
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            {chr(10).join(includes)}


            @app.get("/health")
            async def health_check() -> dict[str, str]:
                return {{"status": "healthy"}}


            @app.get("/ready")
            async def readiness_check() -> dict[str, str]:
                return {{"status": "ready"}}
        ''')

    def _gen_router(self, module: str, endpoints: list[dict[str, str]]) -> str:
        """Generate a FastAPI router for a given module."""
        class_name = module.replace("_", " ").title().replace(" ", "")
        return textwrap.dedent(f'''\
            """Router for {module} endpoints."""

            from __future__ import annotations

            from uuid import UUID

            from fastapi import APIRouter, Depends, HTTPException, status

            from backend.models.{module} import {class_name}Create, {class_name}Response
            from backend.services.{module} import {class_name}Service

            router = APIRouter()


            @router.get("/", response_model=list[{class_name}Response])
            async def list_{module}s(
                page: int = 1,
                page_size: int = 20,
                service: {class_name}Service = Depends(),
            ) -> list[{class_name}Response]:
                """List all {module}s with pagination."""
                return await service.list_all(page=page, page_size=page_size)


            @router.post("/", response_model={class_name}Response, status_code=status.HTTP_201_CREATED)
            async def create_{module}(
                payload: {class_name}Create,
                service: {class_name}Service = Depends(),
            ) -> {class_name}Response:
                """Create a new {module}."""
                return await service.create(payload)


            @router.get("/{{item_id}}", response_model={class_name}Response)
            async def get_{module}(
                item_id: UUID,
                service: {class_name}Service = Depends(),
            ) -> {class_name}Response:
                """Retrieve a {module} by ID."""
                result = await service.get_by_id(item_id)
                if result is None:
                    raise HTTPException(status_code=404, detail="{class_name} not found")
                return result


            @router.put("/{{item_id}}", response_model={class_name}Response)
            async def update_{module}(
                item_id: UUID,
                payload: {class_name}Create,
                service: {class_name}Service = Depends(),
            ) -> {class_name}Response:
                """Update an existing {module}."""
                result = await service.update(item_id, payload)
                if result is None:
                    raise HTTPException(status_code=404, detail="{class_name} not found")
                return result
        ''')

    def _gen_model(self, module: str) -> str:
        class_name = module.replace("_", " ").title().replace(" ", "")
        return textwrap.dedent(f'''\
            """Pydantic models for {module}."""

            from __future__ import annotations

            from datetime import datetime
            from uuid import UUID

            from pydantic import BaseModel, Field


            class {class_name}Base(BaseModel):
                """Shared fields."""
                status: str = Field(default="active", max_length=50)


            class {class_name}Create({class_name}Base):
                """Payload for creating a {module}."""


            class {class_name}Response({class_name}Base):
                """Full representation returned by the API."""
                id: UUID
                created_at: datetime
                updated_at: datetime

                model_config = {{"from_attributes": True}}
        ''')

    def _gen_service(self, module: str) -> str:
        class_name = module.replace("_", " ").title().replace(" ", "")
        return textwrap.dedent(f'''\
            """Service layer for {module} business logic."""

            from __future__ import annotations

            from uuid import UUID

            from backend.models.{module} import {class_name}Create, {class_name}Response


            class {class_name}Service:
                """Handles {module} operations."""

                async def list_all(self, page: int = 1, page_size: int = 20) -> list[{class_name}Response]:
                    """Return paginated list of {module}s."""
                    # TODO: replace with real DB query
                    return []

                async def get_by_id(self, item_id: UUID) -> {class_name}Response | None:
                    """Fetch a single {module} by primary key."""
                    # TODO: replace with real DB query
                    return None

                async def create(self, payload: {class_name}Create) -> {class_name}Response:
                    """Persist a new {module}."""
                    # TODO: replace with real DB insert
                    raise NotImplementedError

                async def update(self, item_id: UUID, payload: {class_name}Create) -> {class_name}Response | None:
                    """Update an existing {module}."""
                    # TODO: replace with real DB update
                    return None
        ''')

    def _gen_config(self) -> str:
        return textwrap.dedent('''\
            """Application configuration loaded from environment variables."""

            from __future__ import annotations

            from pydantic_settings import BaseSettings


            class Settings(BaseSettings):
                """Central settings — reads from env / .env file."""

                app_name: str = "InsureOS"
                debug: bool = False
                database_url: str = "postgresql+asyncpg://localhost/insure_os"
                redis_url: str = "redis://localhost:6379/0"
                jwt_secret: str = "CHANGE_ME"
                jwt_access_minutes: int = 15
                jwt_refresh_days: int = 7

                model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


            settings = Settings()
        ''')

    def _gen_deps(self) -> str:
        return textwrap.dedent('''\
            """Shared FastAPI dependencies (DB session, current user, etc.)."""

            from __future__ import annotations

            from typing import AsyncGenerator


            async def get_db() -> AsyncGenerator[None, None]:
                """Yield a database session.  Placeholder until SQLAlchemy is wired."""
                # TODO: wire up async SQLAlchemy session
                yield None
        ''')
