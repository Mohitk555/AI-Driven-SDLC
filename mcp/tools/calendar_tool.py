"""Google Calendar integration tool for the MCP layer."""

from __future__ import annotations

import os
from typing import Any

import httpx

from mcp.tools.base_tool import BaseTool


class CalendarTool(BaseTool):
    """Interact with Google Calendar via its REST API.

    Supported actions:
        - ``get_events``   — list upcoming events
        - ``create_event`` — create a new calendar event
    """

    _CALENDAR_API = "https://www.googleapis.com/calendar/v3"

    # ------------------------------------------------------------------
    # BaseTool properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "Google Calendar integration (events, scheduling)."

    @property
    def required_params(self) -> dict[str, list[str]]:
        return {
            "get_events": [],
            "create_event": ["summary", "start", "end"],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _config(self) -> tuple[str, str]:
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        return calendar_id, api_key

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._CALENDAR_API,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=15.0,
        )

    # ------------------------------------------------------------------
    # Execute dispatcher
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.validate_params(params):
            return self._fail("Invalid or missing parameters for calendar action.")

        action: str = params["action"]
        try:
            handler = {
                "get_events": self._get_events,
                "create_event": self._create_event,
            }.get(action)

            if handler is None:
                return self._fail(f"Unknown calendar action: {action}")

            return await handler(params)
        except httpx.HTTPStatusError as exc:
            return self._fail(
                f"Google Calendar API error ({exc.response.status_code}): {exc.response.text[:300]}"
            )
        except httpx.RequestError as exc:
            return self._fail(f"Google Calendar request failed: {str(exc)[:300]}")
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Unexpected error in calendar.{action}: {type(exc).__name__}")

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _get_events(self, params: dict[str, Any]) -> dict[str, Any]:
        calendar_id, api_key = self._config()
        max_results: int = params.get("max_results", 10)
        time_min: str | None = params.get("time_min")

        query_params: dict[str, Any] = {
            "key": api_key,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            query_params["timeMin"] = time_min

        async with self._client() as client:
            resp = await client.get(
                f"/calendars/{calendar_id}/events",
                params=query_params,
            )
            resp.raise_for_status()
            data = resp.json()
            events = [
                {
                    "id": ev.get("id"),
                    "summary": ev.get("summary"),
                    "start": ev.get("start"),
                    "end": ev.get("end"),
                    "attendees": [a.get("email") for a in ev.get("attendees", [])],
                }
                for ev in data.get("items", [])
            ]
            return self._ok({"events": events})

    async def _create_event(self, params: dict[str, Any]) -> dict[str, Any]:
        calendar_id, api_key = self._config()
        summary: str = params["summary"]
        start: str = params["start"]  # ISO 8601 datetime string
        end: str = params["end"]      # ISO 8601 datetime string
        description: str = params.get("description", "")
        attendees: list[str] = params.get("attendees", [])
        timezone: str = params.get("timezone", "UTC")

        event_body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }
        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        async with self._client() as client:
            resp = await client.post(
                f"/calendars/{calendar_id}/events",
                params={"key": api_key},
                json=event_body,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._ok({
                "id": data.get("id"),
                "summary": data.get("summary"),
                "html_link": data.get("htmlLink"),
                "start": data.get("start"),
                "end": data.get("end"),
            })
