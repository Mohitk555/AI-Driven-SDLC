"""Slack integration tool for the MCP layer."""

from __future__ import annotations

import os
from typing import Any

import httpx

from mcp.tools.base_tool import BaseTool


class SlackTool(BaseTool):
    """Interact with Slack via its Web API.

    Supported actions:
        - ``send_message``      — post a message to a channel
        - ``send_notification`` — post a styled notification block to a channel
    """

    # ------------------------------------------------------------------
    # BaseTool properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "slack"

    @property
    def description(self) -> str:
        return "Slack messaging integration (messages, notifications)."

    @property
    def required_params(self) -> dict[str, list[str]]:
        return {
            "send_message": ["text"],
            "send_notification": ["title", "text"],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _config(self) -> tuple[str, str]:
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        default_channel = os.environ.get("SLACK_DEFAULT_CHANNEL", "#general")
        return token, default_channel

    def _client(self) -> httpx.AsyncClient:
        token, _ = self._config()
        return httpx.AsyncClient(
            base_url="https://slack.com/api",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=15.0,
        )

    # ------------------------------------------------------------------
    # Execute dispatcher
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.validate_params(params):
            return self._fail("Invalid or missing parameters for slack action.")

        action: str = params["action"]
        try:
            handler = {
                "send_message": self._send_message,
                "send_notification": self._send_notification,
            }.get(action)

            if handler is None:
                return self._fail(f"Unknown slack action: {action}")

            return await handler(params)
        except httpx.HTTPStatusError as exc:
            return self._fail(f"Slack API error ({exc.response.status_code}): {exc.response.text[:300]}")
        except httpx.RequestError as exc:
            return self._fail(f"Slack request failed: {str(exc)[:300]}")
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Unexpected error in slack.{action}: {type(exc).__name__}")

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        _, default_channel = self._config()
        channel: str = params.get("channel", default_channel)
        text: str = params["text"]

        async with self._client() as client:
            resp = await client.post(
                "/chat.postMessage",
                json={"channel": channel, "text": text},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return self._fail(f"Slack API responded with error: {data.get('error', 'unknown')}")
            return self._ok({"channel": data.get("channel"), "ts": data.get("ts")})

    async def _send_notification(self, params: dict[str, Any]) -> dict[str, Any]:
        _, default_channel = self._config()
        channel: str = params.get("channel", default_channel)
        title: str = params["title"]
        text: str = params["text"]
        color: str = params.get("color", "#36a64f")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title, "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
        ]
        attachments = [{"color": color, "blocks": blocks}]

        async with self._client() as client:
            resp = await client.post(
                "/chat.postMessage",
                json={
                    "channel": channel,
                    "text": title,  # Fallback for notifications
                    "attachments": attachments,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return self._fail(f"Slack API responded with error: {data.get('error', 'unknown')}")
            return self._ok({"channel": data.get("channel"), "ts": data.get("ts")})
