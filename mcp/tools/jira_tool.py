"""Jira integration tool for the MCP layer."""

from __future__ import annotations

import os
from typing import Any

import httpx

from mcp.tools.base_tool import BaseTool


class JiraTool(BaseTool):
    """Interact with Jira via its REST API.

    Supported actions:
        - ``create_ticket``  — create a new issue
        - ``update_ticket``  — update fields on an existing issue
        - ``get_ticket``     — fetch a single issue by key
        - ``get_sprint``     — get the active sprint for the configured board
        - ``search_tickets`` — run a JQL query
    """

    # ------------------------------------------------------------------
    # BaseTool properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "jira"

    @property
    def description(self) -> str:
        return "Jira project-management integration (tickets, sprints, search)."

    @property
    def required_params(self) -> dict[str, list[str]]:
        return {
            "create_ticket": ["summary", "issue_type"],
            "update_ticket": ["ticket_key", "fields"],
            "get_ticket": ["ticket_key"],
            "get_sprint": ["board_id"],
            "search_tickets": ["jql"],
        }

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _config(self) -> tuple[str, str, str, str]:
        """Return (base_url, email, token, project_key) from env."""
        base_url = os.environ.get("JIRA_BASE_URL", "")
        email = os.environ.get("JIRA_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")
        project_key = os.environ.get("JIRA_PROJECT_KEY", "")
        return base_url, email, token, project_key

    def _client(self) -> httpx.AsyncClient:
        base_url, email, token, _ = self._config()
        return httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            auth=(email, token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Execute dispatcher
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.validate_params(params):
            return self._fail("Invalid or missing parameters for jira action.")

        action: str = params["action"]
        try:
            handler = {
                "create_ticket": self._create_ticket,
                "update_ticket": self._update_ticket,
                "get_ticket": self._get_ticket,
                "get_sprint": self._get_sprint,
                "search_tickets": self._search_tickets,
            }.get(action)

            if handler is None:
                return self._fail(f"Unknown jira action: {action}")

            return await handler(params)
        except httpx.HTTPStatusError as exc:
            return self._fail(f"Jira API error ({exc.response.status_code}): {exc.response.text[:300]}")
        except httpx.RequestError as exc:
            return self._fail(f"Jira request failed: {str(exc)[:300]}")
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Unexpected error in jira.{action}: {type(exc).__name__}")

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _create_ticket(self, params: dict[str, Any]) -> dict[str, Any]:
        _, _, _, project_key = self._config()
        resolved_project_key = params.get("project_key") or params.get("project") or project_key
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": resolved_project_key},
                "summary": params["summary"],
                "issuetype": {"name": params["issue_type"]},
            }
        }
        if "description" in params:
            payload["fields"]["description"] = params["description"]
        if "assignee" in params:
            payload["fields"]["assignee"] = {"accountId": params["assignee"]}
        if "labels" in params:
            payload["fields"]["labels"] = params["labels"]
        if "priority" in params:
            payload["fields"]["priority"] = {"name": params["priority"]}

        async with self._client() as client:
            resp = await client.post("/rest/api/3/issue", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self._ok({"key": data["key"], "id": data["id"], "self": data["self"]})

    async def _update_ticket(self, params: dict[str, Any]) -> dict[str, Any]:
        ticket_key: str = params["ticket_key"]
        fields: dict[str, Any] = params["fields"]

        async with self._client() as client:
            resp = await client.put(f"/rest/api/3/issue/{ticket_key}", json={"fields": fields})
            resp.raise_for_status()
            return self._ok({"ticket_key": ticket_key, "updated": True})

    async def _get_ticket(self, params: dict[str, Any]) -> dict[str, Any]:
        ticket_key: str = params["ticket_key"]

        async with self._client() as client:
            resp = await client.get(f"/rest/api/3/issue/{ticket_key}")
            resp.raise_for_status()
            data = resp.json()
            return self._ok({
                "key": data["key"],
                "summary": data["fields"].get("summary"),
                "status": data["fields"].get("status", {}).get("name"),
                "assignee": data["fields"].get("assignee"),
                "description": data["fields"].get("description"),
            })

    async def _get_sprint(self, params: dict[str, Any]) -> dict[str, Any]:
        board_id: str = str(params["board_id"])

        async with self._client() as client:
            resp = await client.get(
                f"/rest/agile/1.0/board/{board_id}/sprint",
                params={"state": "active"},
            )
            resp.raise_for_status()
            data = resp.json()
            sprints = data.get("values", [])
            return self._ok({"sprints": sprints})

    async def _search_tickets(self, params: dict[str, Any]) -> dict[str, Any]:
        jql: str = params["jql"]
        max_results: int = params.get("max_results", 50)

        async with self._client() as client:
            resp = await client.post(
                "/rest/api/3/search",
                json={"jql": jql, "maxResults": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
            issues = [
                {
                    "key": issue["key"],
                    "summary": issue["fields"].get("summary"),
                    "status": issue["fields"].get("status", {}).get("name"),
                }
                for issue in data.get("issues", [])
            ]
            return self._ok({"total": data.get("total", 0), "issues": issues})
