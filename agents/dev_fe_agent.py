"""Frontend Developer Agent — generates Next.js / React components."""

from __future__ import annotations

import logging
import re
import textwrap
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DevFrontendAgent(BaseAgent):
    """Generates Next.js / React frontend code from architecture and requirements.

    Reads ``memory/architecture.md`` for component structure and API
    contracts, then produces TypeScript/React files under ``/frontend/``.
    """

    agent_id: str = "dev_fe_agent"
    role: str = "Frontend Developer"
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
        """Generate frontend code artifacts and Git tool-calls."""
        try:
            self.load_constitution()

            architecture = self.read_memory("architecture.md")
            requirements = self.read_memory("requirements.md")

            if not architecture and not requirements:
                return self._fail(
                    "No architecture or requirements found. "
                    "Run the Tech Lead or PM Agent first."
                )

            components = self._identify_ui_components(architecture or "", requirements or "")
            api_endpoints = self._parse_api_endpoints(architecture or "")
            generated_files = self._generate_code(components, api_endpoints)

            ticket_id = context.get("ticket_id")
            ticket_segment = ticket_id or "no-ticket"
            branch_name = f"feature/{ticket_segment}-frontend-implementation"
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
                        "commit_message": f"feat(frontend): add UI components for {ticket_segment}",
                    },
                ),
                self.create_tool_call(
                    "github.create_pr",
                    {
                        "repo": "insure-os",
                        "title": f"[{ticket_segment}] Frontend UI implementation",
                        "body": (
                            f"## Changes\n"
                            f"- Generated {len(generated_files)} frontend files\n"
                            f"- {len(components)} UI components\n"
                            f"- API integration hooks\n\n"
                            f"## Testing\n"
                            f"- [ ] Verify pages render\n"
                            f"- [ ] Check API integration\n"
                            f"- [ ] Responsive layout check"
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
                f"Generated {len(generated_files)} frontend files with "
                f"{len(components)} UI components. Branch: {branch_name}."
            )
            return self._ok(
                output=output,
                tool_calls=tool_calls,
                metadata={
                    "branch": branch_name,
                    "files_generated": list(generated_files.keys()),
                    "component_count": len(components),
                },
            )

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _identify_ui_components(self, architecture: str, requirements: str) -> list[dict[str, str]]:
        """Derive UI components from architecture and requirements."""
        components: list[dict[str, str]] = [
            {"name": "Layout", "description": "Root layout with navigation and footer"},
            {"name": "Dashboard", "description": "Main dashboard with summary cards"},
            {"name": "LoginForm", "description": "Authentication login form"},
        ]

        service_names = re.findall(r"\|\s*([A-Z][\w\s]+?Service)\s*\|", architecture)
        for svc in service_names:
            entity = svc.replace(" Service", "")
            components.extend([
                {"name": f"{entity}List", "description": f"Table listing all {entity.lower()}s"},
                {"name": f"{entity}Detail", "description": f"Detail view for a single {entity.lower()}"},
                {"name": f"{entity}Form", "description": f"Create / edit form for {entity.lower()}"},
            ])

        return components

    def _parse_api_endpoints(self, architecture: str) -> list[dict[str, str]]:
        """Extract API endpoints for hook generation."""
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
        components: list[dict[str, str]],
        endpoints: list[dict[str, str]],
    ) -> dict[str, str]:
        """Produce frontend files as a dict of ``{filepath: content}``."""
        files: dict[str, str] = {}

        # Layout
        files["frontend/src/app/layout.tsx"] = self._gen_layout()
        files["frontend/src/app/page.tsx"] = self._gen_home_page()

        # Per-component files
        for comp in components:
            kebab = self._to_kebab(comp["name"])
            files[f"frontend/src/components/{kebab}.tsx"] = self._gen_component(comp)

        # API hooks
        if endpoints:
            files["frontend/src/lib/api.ts"] = self._gen_api_client()
            files["frontend/src/hooks/use-api.ts"] = self._gen_hooks(endpoints)

        # Types
        files["frontend/src/types/index.ts"] = self._gen_types(components)

        return files

    # ------------------------------------------------------------------
    # Template generators
    # ------------------------------------------------------------------

    def _gen_layout(self) -> str:
        return textwrap.dedent('''\
            import type { Metadata } from "next";
            import "./globals.css";

            export const metadata: Metadata = {
              title: "InsureOS",
              description: "AI-powered Insurance Operating System",
            };

            export default function RootLayout({
              children,
            }: {
              children: React.ReactNode;
            }) {
              return (
                <html lang="en">
                  <body>
                    <nav className="border-b px-6 py-3 flex items-center justify-between">
                      <span className="font-bold text-lg">InsureOS</span>
                      <div className="flex gap-4">
                        <a href="/dashboard">Dashboard</a>
                        <a href="/policies">Policies</a>
                        <a href="/claims">Claims</a>
                      </div>
                    </nav>
                    <main className="p-6">{children}</main>
                  </body>
                </html>
              );
            }
        ''')

    def _gen_home_page(self) -> str:
        return textwrap.dedent('''\
            export default function HomePage() {
              return (
                <div className="max-w-4xl mx-auto py-12">
                  <h1 className="text-3xl font-bold mb-4">Welcome to InsureOS</h1>
                  <p className="text-gray-600">
                    AI-powered Insurance Operating System. Navigate to the dashboard to get started.
                  </p>
                </div>
              );
            }
        ''')

    def _gen_component(self, comp: dict[str, str]) -> str:
        name = comp["name"]
        desc = comp["description"]
        return textwrap.dedent(f'''\
            "use client";

            interface I{name}Props {{
              className?: string;
            }}

            /**
             * {desc}
             */
            export default function {name}({{ className }}: I{name}Props) {{
              return (
                <section className={{className}}>
                  <h2 className="text-xl font-semibold mb-4">{name}</h2>
                  {{/* TODO: implement {name} */}}
                  <p className="text-gray-500">{desc}</p>
                </section>
              );
            }}
        ''')

    def _gen_api_client(self) -> str:
        return textwrap.dedent('''\
            const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

            export async function apiFetch<T>(
              path: string,
              options?: RequestInit
            ): Promise<T> {
              const res = await fetch(`${API_BASE}${path}`, {
                headers: { "Content-Type": "application/json", ...options?.headers },
                ...options,
              });
              if (!res.ok) {
                throw new Error(`API error ${res.status}: ${await res.text()}`);
              }
              return res.json() as Promise<T>;
            }
        ''')

    def _gen_hooks(self, endpoints: list[dict[str, str]]) -> str:
        """Generate TanStack Query hooks for each GET endpoint."""
        lines = [
            '"use client";',
            "",
            'import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";',
            'import { apiFetch } from "@/lib/api";',
            "",
        ]
        seen_resources: set[str] = set()
        for ep in endpoints:
            path = ep["path"]
            # Derive a resource name from the path
            segments = [s for s in path.split("/") if s and s != "api" and s != "v1" and not s.startswith("{")]
            resource = segments[-1] if segments else "resource"
            if resource in seen_resources:
                continue
            seen_resources.add(resource)
            pascal = resource.replace("_", " ").title().replace(" ", "")

            lines.extend([
                f"export function use{pascal}() {{",
                f'  return useQuery({{',
                f'    queryKey: ["{resource}"],',
                f'    queryFn: () => apiFetch<unknown[]>("{path}"),',
                f"  }});",
                f"}}",
                "",
            ])
        return "\n".join(lines)

    def _gen_types(self, components: list[dict[str, str]]) -> str:
        """Generate TypeScript interfaces for entity types."""
        lines = ["// Auto-generated type definitions for InsureOS", ""]
        seen: set[str] = set()
        for comp in components:
            name = comp["name"]
            # Only generate an interface for entity-related components
            if name.endswith("List") or name.endswith("Detail") or name.endswith("Form"):
                entity = name.replace("List", "").replace("Detail", "").replace("Form", "")
                if entity in seen:
                    continue
                seen.add(entity)
                lines.extend([
                    f"export interface I{entity} {{",
                    "  id: string;",
                    "  status: string;",
                    "  createdAt: string;",
                    "  updatedAt: string;",
                    "}",
                    "",
                ])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _to_kebab(name: str) -> str:
        """Convert PascalCase to kebab-case."""
        s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", name)
        return s.lower()
