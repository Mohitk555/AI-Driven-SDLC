"""DevOps Agent — generates Docker, CI/CD, and deployment configurations."""

from __future__ import annotations

import logging
import textwrap
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DevOpsAgent(BaseAgent):
    """Produces infrastructure and deployment artifacts.

    Generates Dockerfiles, docker-compose configs, GitHub Actions
    pipelines, and health-check implementations aligned with the
    constitution's DevOps requirements (section 11).
    """

    agent_id: str = "devops_agent"
    role: str = "DevOps Engineer"
    permissions: list[str] = [
        "github.create_branch",
        "github.push_code",
        "github.create_pr",
    ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Generate DevOps artifacts and return Git tool-calls."""
        try:
            self.load_constitution()

            lower = message.lower()

            if "docker" in lower or "container" in lower:
                return await self._generate_docker(context)
            if "ci" in lower or "pipeline" in lower or "github action" in lower:
                return await self._generate_cicd(context)
            if "deploy" in lower:
                return await self._generate_deployment(context)

            # Default: full infra setup
            return await self._generate_full_infra(context)

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Full infrastructure
    # ------------------------------------------------------------------

    async def _generate_full_infra(self, context: dict[str, Any]) -> AgentResponse:
        """Generate all DevOps files in one pass."""
        files: dict[str, str] = {}
        files.update(self._docker_files())
        files.update(self._cicd_files())
        files.update(self._deployment_files())

        ticket_id = context.get("ticket_id", "INS-001")
        branch_name = f"feature/{ticket_id}-devops-infrastructure"

        tool_calls: list[ToolCall] = [
            self.create_tool_call(
                "github.create_branch",
                {
              "branch_name": branch_name,
              "base_ref": "develop",
                },
            ),
            self.create_tool_call(
                "github.push_code",
                {
                    "branch": branch_name,
                    "files": files,
                    "commit_message": f"ci(infra): add Docker, CI/CD, and deployment configs for {ticket_id}",
                },
            ),
            self.create_tool_call(
                "github.create_pr",
                {
                    "repo": "insure-os",
                    "title": f"[{ticket_id}] DevOps infrastructure setup",
                    "body": (
                        "## Changes\n"
                        "- Dockerfiles for backend and frontend (multi-stage)\n"
                        "- docker-compose for local development\n"
                        "- GitHub Actions CI/CD pipeline\n"
                        "- Deployment configurations per environment\n\n"
                        "## Testing\n"
                        "- [ ] `docker compose up` builds and runs\n"
                        "- [ ] CI pipeline passes on push\n"
                        "- [ ] Health endpoints respond"
                    ),
                    "head": branch_name,
                    "base": "develop",
                },
            ),
        ]

        output = (
            f"Generated {len(files)} DevOps files: Docker, CI/CD, "
            f"and deployment configs. Branch: {branch_name}."
        )
        return self._ok(
            output=output,
            tool_calls=tool_calls,
            metadata={
                "branch": branch_name,
                "files_generated": list(files.keys()),
            },
        )

    # ------------------------------------------------------------------
    # Scoped generators
    # ------------------------------------------------------------------

    async def _generate_docker(self, context: dict[str, Any]) -> AgentResponse:
        files = self._docker_files()
        output = f"Generated {len(files)} Docker files."
        return self._ok(output=output, metadata={"generated_files": files})

    async def _generate_cicd(self, context: dict[str, Any]) -> AgentResponse:
        files = self._cicd_files()
        output = f"Generated {len(files)} CI/CD pipeline files."
        return self._ok(output=output, metadata={"generated_files": files})

    async def _generate_deployment(self, context: dict[str, Any]) -> AgentResponse:
        files = self._deployment_files()
        output = f"Generated {len(files)} deployment config files."
        return self._ok(output=output, metadata={"generated_files": files})

    # ------------------------------------------------------------------
    # File content generators
    # ------------------------------------------------------------------

    def _docker_files(self) -> dict[str, str]:
        """Generate Docker-related files."""
        return {
            "backend/Dockerfile": self._backend_dockerfile(),
            "frontend/Dockerfile": self._frontend_dockerfile(),
            "docker-compose.yml": self._docker_compose(),
            "docker-compose.prod.yml": self._docker_compose_prod(),
            ".dockerignore": self._dockerignore(),
        }

    def _cicd_files(self) -> dict[str, str]:
        """Generate GitHub Actions workflow files."""
        return {
            ".github/workflows/ci.yml": self._ci_workflow(),
            ".github/workflows/deploy.yml": self._deploy_workflow(),
        }

    def _deployment_files(self) -> dict[str, str]:
        """Generate environment-specific deployment configs."""
        return {
            "deploy/nginx.conf": self._nginx_conf(),
            "deploy/.env.example": self._env_example(),
        }

    # ------------------------------------------------------------------
    # Docker templates
    # ------------------------------------------------------------------

    def _backend_dockerfile(self) -> str:
        return textwrap.dedent('''\
            # ---------- build stage ----------
            FROM python:3.11-slim AS builder

            WORKDIR /app
            RUN pip install --no-cache-dir poetry
            COPY pyproject.toml poetry.lock* ./
            RUN poetry config virtualenvs.create false \\
                && poetry install --no-dev --no-interaction --no-ansi

            # ---------- production stage ----------
            FROM python:3.11-slim

            WORKDIR /app
            COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
            COPY --from=builder /usr/local/bin /usr/local/bin
            COPY backend/ ./backend/

            EXPOSE 8000

            HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
                CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

            CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
        ''')

    def _frontend_dockerfile(self) -> str:
        return textwrap.dedent('''\
            # ---------- deps ----------
            FROM node:20-alpine AS deps
            WORKDIR /app
            COPY frontend/package.json frontend/package-lock.json* ./
            RUN npm ci

            # ---------- build ----------
            FROM node:20-alpine AS builder
            WORKDIR /app
            COPY --from=deps /app/node_modules ./node_modules
            COPY frontend/ ./
            RUN npm run build

            # ---------- production ----------
            FROM node:20-alpine
            WORKDIR /app
            ENV NODE_ENV=production

            COPY --from=builder /app/.next/standalone ./
            COPY --from=builder /app/.next/static ./.next/static
            COPY --from=builder /app/public ./public

            EXPOSE 3000

            HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
                CMD ["wget", "-qO-", "http://localhost:3000/api/health"]

            CMD ["node", "server.js"]
        ''')

    def _docker_compose(self) -> str:
        return textwrap.dedent('''\
            version: "3.9"

            services:
              backend:
                build:
                  context: .
                  dockerfile: backend/Dockerfile
                ports:
                  - "8000:8000"
                env_file: .env
                depends_on:
                  db:
                    condition: service_healthy
                  redis:
                    condition: service_healthy

              frontend:
                build:
                  context: .
                  dockerfile: frontend/Dockerfile
                ports:
                  - "3000:3000"
                environment:
                  NEXT_PUBLIC_API_URL: http://backend:8000

              db:
                image: postgres:16-alpine
                environment:
                  POSTGRES_DB: insure_os
                  POSTGRES_USER: insure
                  POSTGRES_PASSWORD: localdev
                ports:
                  - "5432:5432"
                volumes:
                  - pgdata:/var/lib/postgresql/data
                healthcheck:
                  test: ["CMD-SHELL", "pg_isready -U insure"]
                  interval: 5s
                  timeout: 5s
                  retries: 5

              redis:
                image: redis:7-alpine
                ports:
                  - "6379:6379"
                healthcheck:
                  test: ["CMD", "redis-cli", "ping"]
                  interval: 5s
                  timeout: 5s
                  retries: 5

            volumes:
              pgdata:
        ''')

    def _docker_compose_prod(self) -> str:
        return textwrap.dedent('''\
            version: "3.9"

            # Production overrides — extend the base docker-compose.yml
            # Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

            services:
              backend:
                restart: always
                deploy:
                  replicas: 2
                  resources:
                    limits:
                      cpus: "1.0"
                      memory: 512M

              frontend:
                restart: always
                deploy:
                  replicas: 2
                  resources:
                    limits:
                      cpus: "0.5"
                      memory: 256M

              db:
                restart: always
                volumes:
                  - /data/postgres:/var/lib/postgresql/data

              redis:
                restart: always
        ''')

    def _dockerignore(self) -> str:
        return textwrap.dedent('''\
            __pycache__
            *.pyc
            .git
            .env
            .venv
            node_modules
            .next
            dist
            *.egg-info
            .pytest_cache
            .mypy_cache
            coverage/
        ''')

    # ------------------------------------------------------------------
    # CI/CD templates
    # ------------------------------------------------------------------

    def _ci_workflow(self) -> str:
        return textwrap.dedent('''\
            name: CI

            on:
              push:
                branches: [develop, "feature/**", "bugfix/**"]
              pull_request:
                branches: [develop, main]

            jobs:
              lint:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                    with:
                      python-version: "3.11"
                  - run: pip install ruff
                  - run: ruff check backend/ agents/ orchestrator/

              test-backend:
                runs-on: ubuntu-latest
                needs: lint
                services:
                  postgres:
                    image: postgres:16-alpine
                    env:
                      POSTGRES_DB: insure_os_test
                      POSTGRES_USER: test
                      POSTGRES_PASSWORD: test
                    ports:
                      - 5432:5432
                    options: >-
                      --health-cmd "pg_isready -U test"
                      --health-interval 5s
                      --health-timeout 5s
                      --health-retries 5
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                    with:
                      python-version: "3.11"
                  - run: pip install poetry && poetry install
                  - run: poetry run pytest --cov=backend --cov-report=xml
                    env:
                      DATABASE_URL: postgresql://test:test@localhost:5432/insure_os_test

              test-frontend:
                runs-on: ubuntu-latest
                needs: lint
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-node@v4
                    with:
                      node-version: "20"
                  - run: cd frontend && npm ci && npm test -- --coverage

              build:
                runs-on: ubuntu-latest
                needs: [test-backend, test-frontend]
                steps:
                  - uses: actions/checkout@v4
                  - run: docker compose build
        ''')

    def _deploy_workflow(self) -> str:
        return textwrap.dedent('''\
            name: Deploy

            on:
              push:
                branches: [main]

            jobs:
              deploy-staging:
                runs-on: ubuntu-latest
                environment: staging
                steps:
                  - uses: actions/checkout@v4
                  - name: Build images
                    run: docker compose -f docker-compose.yml -f docker-compose.prod.yml build
                  - name: Push to registry
                    run: echo "TODO — push to container registry"
                  - name: Deploy to staging
                    run: echo "TODO — deploy to staging environment"

              deploy-production:
                runs-on: ubuntu-latest
                needs: deploy-staging
                environment: production
                steps:
                  - uses: actions/checkout@v4
                  - name: Deploy to production
                    run: echo "TODO — deploy to production with zero-downtime"
        ''')

    # ------------------------------------------------------------------
    # Deployment templates
    # ------------------------------------------------------------------

    def _nginx_conf(self) -> str:
        return textwrap.dedent('''\
            upstream backend {
                server backend:8000;
            }

            upstream frontend {
                server frontend:3000;
            }

            server {
                listen 80;
                server_name _;

                # Frontend
                location / {
                    proxy_pass http://frontend;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }

                # Backend API
                location /api/ {
                    proxy_pass http://backend;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                }

                # Health checks
                location /health {
                    proxy_pass http://backend;
                }

                location /ready {
                    proxy_pass http://backend;
                }
            }
        ''')

    def _env_example(self) -> str:
        return textwrap.dedent('''\
            # InsureOS environment variables
            # Copy to .env and fill in real values — NEVER commit .env

            APP_NAME=InsureOS
            DEBUG=false

            # Database
            DATABASE_URL=postgresql+asyncpg://user:password@db:5432/insure_os

            # Redis
            REDIS_URL=redis://redis:6379/0

            # JWT
            JWT_SECRET=CHANGE_ME_IN_PRODUCTION
            JWT_ACCESS_MINUTES=15
            JWT_REFRESH_DAYS=7

            # External services
            JIRA_API_URL=https://yourorg.atlassian.net
            JIRA_API_TOKEN=
            GITHUB_TOKEN=
            SLACK_WEBHOOK_URL=
        ''')
