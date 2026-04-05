"""Background task scheduler for periodic SDLC operations.

Manages recurring jobs — daily standups, hourly status updates, and
pipeline health checks — using pure ``asyncio`` (no external scheduler
dependencies).  All external actions are dispatched through the central
MCP server.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine

from mcp.mcp_server import MCPServer

logger = logging.getLogger(__name__)


# ======================================================================
# Data models
# ======================================================================

@dataclass
class ScheduledJob:
    """Metadata for a single recurring job managed by the scheduler."""

    name: str
    interval_seconds: float
    callback: Callable[[], Coroutine[Any, Any, None]]
    task: asyncio.Task[None] | None = None
    last_run: datetime | None = None
    next_run: datetime | None = None
    enabled: bool = True


# ======================================================================
# TaskScheduler
# ======================================================================

class TaskScheduler:
    """Async scheduler for periodic background SDLC jobs.

    Parameters
    ----------
    mcp_server:
        The central :class:`MCPServer` used to dispatch tool calls
        (Jira, Slack, Calendar, etc.).
    standup_hour:
        Hour of the day (0-23) at which the daily standup fires.
    timezone:
        IANA timezone string.  Only ``"UTC"`` and fixed-offset strings
        are supported without third-party libraries; for named zones,
        ensure ``zoneinfo`` is available (Python 3.9+).
    """

    # Agent identity used for MCP permission checks on scheduler calls.
    _AGENT_ID = "scrum_agent"

    def __init__(
        self,
        mcp_server: MCPServer,
        standup_hour: int = 17,
        timezone: str = "UTC",
    ) -> None:
        self._mcp = mcp_server
        self._standup_hour = standup_hour
        self._tz = self._resolve_timezone(timezone)
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Timezone helper
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_timezone(name: str) -> timezone:
        """Return a :class:`datetime.timezone` for *name*.

        Falls back to ``zoneinfo.ZoneInfo`` when available, otherwise
        only ``"UTC"`` and ``"UTC+N"`` / ``"UTC-N"`` are accepted.
        """
        if name == "UTC":
            return timezone.utc
        # Try zoneinfo (stdlib in 3.9+).
        try:
            from zoneinfo import ZoneInfo  # noqa: WPS433

            zone = ZoneInfo(name)
            # Convert to a fixed offset for scheduling simplicity.
            offset = datetime.now(zone).utcoffset()
            if offset is not None:
                return timezone(offset)
        except (ImportError, KeyError):
            pass
        # Fallback: parse "UTC+5", "UTC-3:30", etc.
        if name.startswith("UTC"):
            sign = 1
            rest = name[3:]
            if rest.startswith("+"):
                rest = rest[1:]
            elif rest.startswith("-"):
                sign = -1
                rest = rest[1:]
            try:
                parts = rest.split(":")
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                return timezone(timedelta(hours=sign * hours, minutes=sign * minutes))
            except (ValueError, IndexError):
                pass
        logger.warning("Unrecognised timezone '%s', falling back to UTC.", name)
        return timezone.utc

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Register and launch all default scheduled jobs."""
        if self._running:
            logger.warning("Scheduler is already running.")
            return

        self._running = True
        logger.info("Starting TaskScheduler (standup at %02d:00, tz=%s).", self._standup_hour, self._tz)

        # 1) Daily standup — fires once per day at the configured hour.
        await self._register_job(
            name="daily_standup",
            interval_seconds=self._seconds_until_next_standup(),
            callback=self._daily_standup_loop,
            one_shot_first_interval=True,
        )

        # 2) Hourly ticket status update.
        await self._register_job(
            name="hourly_status_update",
            interval_seconds=3600,
            callback=self.run_status_update,
        )

        # 3) Pipeline health check every 5 minutes.
        await self._register_job(
            name="pipeline_health_check",
            interval_seconds=300,
            callback=self._run_pipeline_health_check,
        )

    async def stop(self) -> None:
        """Cancel every running job and reset state."""
        self._running = False
        async with self._lock:
            for job in self._jobs.values():
                if job.task and not job.task.done():
                    job.task.cancel()
            # Wait for cancellation to propagate.
            tasks = [j.task for j in self._jobs.values() if j.task]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self._jobs.clear()
        logger.info("TaskScheduler stopped — all jobs cancelled.")

    # ------------------------------------------------------------------
    # Job registration / management
    # ------------------------------------------------------------------

    async def _register_job(
        self,
        name: str,
        interval_seconds: float,
        callback: Callable[[], Coroutine[Any, Any, None]],
        *,
        one_shot_first_interval: bool = False,
    ) -> None:
        """Create a :class:`ScheduledJob` and start its background loop."""
        async with self._lock:
            job = ScheduledJob(
                name=name,
                interval_seconds=interval_seconds,
                callback=callback,
                next_run=datetime.now(self._tz) + timedelta(seconds=interval_seconds),
            )
            self._jobs[name] = job
            job.task = asyncio.create_task(
                self._run_loop(job, one_shot_first_interval=one_shot_first_interval),
                name=f"scheduler-{name}",
            )
        logger.info("Registered job '%s' (interval=%ss).", name, interval_seconds)

    async def _run_loop(
        self,
        job: ScheduledJob,
        *,
        one_shot_first_interval: bool = False,
    ) -> None:
        """Infinite loop that sleeps then executes *job.callback*."""
        try:
            # First sleep — for the standup this is the time-until-target;
            # for interval jobs this is the regular interval.
            await asyncio.sleep(job.interval_seconds)

            while self._running:
                if job.enabled:
                    job.last_run = datetime.now(self._tz)
                    try:
                        await job.callback()
                    except Exception:
                        logger.exception("Error in scheduled job '%s'.", job.name)

                # After the first (possibly custom) interval, normalise.
                if one_shot_first_interval and job.name == "daily_standup":
                    job.interval_seconds = 86400  # 24 hours

                job.next_run = datetime.now(self._tz) + timedelta(seconds=job.interval_seconds)
                await asyncio.sleep(job.interval_seconds)

        except asyncio.CancelledError:
            logger.debug("Job '%s' cancelled.", job.name)

    def get_schedule(self) -> list[dict[str, Any]]:
        """Return a snapshot of all registered jobs and their timings."""
        return [
            {
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "enabled": job.enabled,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
            }
            for job in self._jobs.values()
        ]

    async def update_schedule(self, job_name: str, interval_seconds: float) -> None:
        """Update the interval for an existing job, restarting its loop.

        Parameters
        ----------
        job_name:
            The registered name (e.g. ``"hourly_status_update"``).
        interval_seconds:
            New interval in seconds.  For cron-like expressions, the
            caller is responsible for converting to seconds.
        """
        async with self._lock:
            job = self._jobs.get(job_name)
            if job is None:
                raise ValueError(f"Unknown job: {job_name}")

            # Cancel the existing loop and restart with the new interval.
            if job.task and not job.task.done():
                job.task.cancel()
                try:
                    await job.task
                except asyncio.CancelledError:
                    pass

            job.interval_seconds = interval_seconds
            job.next_run = datetime.now(self._tz) + timedelta(seconds=interval_seconds)
            job.task = asyncio.create_task(
                self._run_loop(job),
                name=f"scheduler-{job.name}",
            )
        logger.info("Updated job '%s' interval to %ss.", job_name, interval_seconds)

    # ------------------------------------------------------------------
    # Standup helpers
    # ------------------------------------------------------------------

    def _seconds_until_next_standup(self) -> float:
        """Compute seconds from *now* to the next standup hour."""
        now = datetime.now(self._tz)
        target = now.replace(hour=self._standup_hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    async def _daily_standup_loop(self) -> None:
        """Wrapper that recalculates the sleep-until-standup each cycle."""
        await self.run_standup()

    # ------------------------------------------------------------------
    # MCP helpers
    # ------------------------------------------------------------------

    async def _mcp_call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an MCP tool call and return the response dict."""
        tool_call = {
            "type": "tool_call",
            "tool": tool,
            "input": params,
        }
        result = await self._mcp.execute(tool_call, agent_id=self._AGENT_ID)
        if not result.get("success"):
            logger.error("MCP call %s failed: %s", tool, result.get("error"))
        return result

    # ------------------------------------------------------------------
    # Job 1 — Daily standup
    # ------------------------------------------------------------------

    async def run_standup(self) -> dict[str, Any]:
        """Fetch sprint + calendar data and post a standup summary to Slack.

        Can be invoked manually or by the daily schedule.

        Returns the Slack notification MCP response.
        """
        logger.info("Running daily standup report.")

        # --- Fetch data in parallel -----------------------------------
        sprint_task = asyncio.create_task(self._fetch_sprint_status())
        calendar_task = asyncio.create_task(self._fetch_today_events())

        sprint_data, calendar_data = await asyncio.gather(
            sprint_task, calendar_task, return_exceptions=True,
        )

        # Gracefully degrade if a source fails.
        if isinstance(sprint_data, BaseException):
            logger.error("Failed to fetch sprint data: %s", sprint_data)
            sprint_data = {}
        if isinstance(calendar_data, BaseException):
            logger.error("Failed to fetch calendar data: %s", calendar_data)
            calendar_data = {}

        # --- Build message --------------------------------------------
        message = self._format_standup_message(sprint_data, calendar_data)

        # --- Post to Slack --------------------------------------------
        sprint_name = sprint_data.get("sprint_name", "Current Sprint")
        result = await self._mcp_call("slack.send_notification", {
            "title": f"\U0001f3c3 Daily Standup \u2014 {sprint_name}",
            "text": message,
            "color": "#36a64f",
        })
        return result

    async def _fetch_sprint_status(self) -> dict[str, Any]:
        """Query Jira for the active sprint's tickets."""
        result = await self._mcp_call("jira.search_tickets", {
            "jql": "sprint in openSprints() ORDER BY status ASC",
        })
        if not result.get("success"):
            return {}

        tickets: list[dict[str, Any]] = result.get("data", {}).get("issues", [])
        done = [t for t in tickets if t.get("status", "").lower() in ("done", "closed")]
        blocked = [t for t in tickets if t.get("status", "").lower() == "blocked"]
        in_progress = [t for t in tickets if t.get("status", "").lower() == "in progress"]

        # Determine sprint name from first ticket if available.
        sprint_name = "Current Sprint"
        if tickets:
            sprint_name = tickets[0].get("sprint", sprint_name)

        return {
            "sprint_name": sprint_name,
            "total": len(tickets),
            "done": done,
            "blocked": blocked,
            "in_progress": in_progress,
            "tickets": tickets,
        }

    async def _fetch_today_events(self) -> dict[str, Any]:
        """Fetch calendar events for today."""
        today = datetime.now(self._tz).strftime("%Y-%m-%d")
        result = await self._mcp_call("calendar.get_events", {"date": today})
        if not result.get("success"):
            return {}
        return result.get("data", {})

    def _format_standup_message(
        self,
        sprint: dict[str, Any],
        calendar: dict[str, Any],
    ) -> str:
        """Build a rich-text standup message."""
        lines: list[str] = []

        # Sprint progress
        total = sprint.get("total", 0)
        done = sprint.get("done", [])
        blocked = sprint.get("blocked", [])
        in_progress = sprint.get("in_progress", [])
        done_count = len(done)
        pct = round((done_count / total) * 100) if total else 0

        lines.append(f"*Sprint Progress:* {done_count}/{total} tickets done ({pct}%)")
        lines.append("")

        # Today's completed tickets
        if done:
            lines.append("*Completed today:*")
            for t in done:
                key = t.get("key", "???")
                summary = t.get("summary", "")
                lines.append(f"  \u2705 {key}: {summary}")
            lines.append("")

        # In progress
        if in_progress:
            lines.append("*In Progress:*")
            for t in in_progress:
                key = t.get("key", "???")
                summary = t.get("summary", "")
                assignee = t.get("assignee", "unassigned")
                lines.append(f"  \U0001f6e0\ufe0f {key}: {summary} ({assignee})")
            lines.append("")

        # Blocked
        if blocked:
            lines.append("*Blocked:*")
            for t in blocked:
                key = t.get("key", "???")
                summary = t.get("summary", "")
                lines.append(f"  \U0001f6d1 {key}: {summary}")
            lines.append("")

        # Upcoming meetings
        events = calendar.get("events", [])
        if events:
            lines.append("*Upcoming Meetings:*")
            for ev in events:
                event_time = ev.get("time", "")
                title = ev.get("title", "Untitled")
                lines.append(f"  \U0001f4c5 {event_time} \u2014 {title}")
        else:
            lines.append("*Upcoming Meetings:* None scheduled.")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Job 2 — Hourly status update
    # ------------------------------------------------------------------

    async def run_status_update(self) -> dict[str, Any]:
        """Query Jira for tickets that changed status in the last hour
        and post a summary to Slack.

        Returns the Slack notification MCP response (or an empty dict if
        there are no changes).
        """
        logger.info("Running hourly ticket status update.")

        one_hour_ago = (datetime.now(self._tz) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        result = await self._mcp_call("jira.search_tickets", {
            "jql": f'status changed AFTER "{one_hour_ago}" ORDER BY updated DESC',
        })

        if not result.get("success"):
            return result

        tickets: list[dict[str, Any]] = result.get("data", {}).get("issues", [])

        if not tickets:
            logger.info("No ticket status changes in the last hour.")
            return {"success": True, "data": {"changes": 0}}

        lines: list[str] = []
        for t in tickets:
            key = t.get("key", "???")
            summary = t.get("summary", "")
            from_status = t.get("from_status", "Unknown")
            to_status = t.get("status", "Unknown")
            assignee = t.get("assignee", "unassigned")
            lines.append(
                f"\U0001f504 {key}: {summary} \u2014 {from_status} \u2192 {to_status} ({assignee})"
            )

        text = "\n".join(lines)
        slack_result = await self._mcp_call("slack.send_notification", {
            "title": f"\U0001f504 Ticket Status Updates \u2014 {len(tickets)} change(s)",
            "text": text,
            "color": "#439FE0",
        })
        return slack_result

    # ------------------------------------------------------------------
    # Job 3 — Pipeline health check
    # ------------------------------------------------------------------

    async def _run_pipeline_health_check(self) -> None:
        """Check running pipelines for stuck or failed stages."""
        logger.info("Running pipeline health check.")

        result = await self._mcp_call("jira.search_tickets", {
            "jql": 'status = "In Pipeline" ORDER BY updated ASC',
        })

        if not result.get("success"):
            return

        tickets: list[dict[str, Any]] = result.get("data", {}).get("issues", [])
        now = datetime.now(self._tz)
        stuck_threshold = timedelta(minutes=30)
        alerts: list[str] = []

        for t in tickets:
            key = t.get("key", "???")
            summary = t.get("summary", "")
            stage = t.get("pipeline_stage", "unknown")
            started_raw = t.get("stage_started_at")

            if not started_raw:
                continue

            try:
                started_at = datetime.fromisoformat(started_raw)
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=self._tz)
            except (ValueError, TypeError):
                logger.warning("Cannot parse stage_started_at for %s: %s", key, started_raw)
                continue

            elapsed = now - started_at
            if elapsed > stuck_threshold:
                minutes = int(elapsed.total_seconds() / 60)
                alerts.append(
                    f"\u26a0\ufe0f {key}: {summary} \u2014 stage *{stage}* stuck for {minutes}m"
                )

        if not alerts:
            logger.debug("All pipelines healthy.")
            return

        text = "\n".join(alerts)
        await self._mcp_call("slack.send_notification", {
            "title": "\U0001f6a8 Pipeline Health Alert",
            "text": text,
            "color": "#FF0000",
        })
        logger.warning("Pipeline health alert sent for %d issue(s).", len(alerts))
