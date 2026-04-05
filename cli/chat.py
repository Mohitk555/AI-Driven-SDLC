from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from typing import Any

import httpx


def _print_banner(base_url: str, session_id: str) -> None:
    print("AI Engineering OS Terminal Chat")
    print(f"Server: {base_url}")
    print(f"Session: {session_id}")
    print("Commands: /help, /new, /session, /quit")


def _print_response(payload: dict[str, Any]) -> None:
    agent_id = payload.get("agent_id", "unknown")
    status = payload.get("status", "unknown")
    intent = payload.get("intent", "unknown")
    message = payload.get("message", "")

    print(f"\n[{agent_id}] status={status} intent={intent}")
    print(message)

    tool_results = ((payload.get("data") or {}).get("tool_results")) or []
    if tool_results:
        ok = sum(1 for r in tool_results if r.get("success"))
        fail = len(tool_results) - ok
        print(f"Tool results: {ok} succeeded, {fail} failed")

    data = payload.get("data") or {}
    pipeline_id = data.get("pipeline_id")
    if pipeline_id:
        print("Pipeline:")
        print(
            f"  id={pipeline_id} status={data.get('pipeline_status')} "
            f"stage={data.get('current_stage')} completed_stages={data.get('stages_completed')}"
        )
        jira_tickets = data.get("jira_tickets") or []
        if jira_tickets:
            print(f"  jira_tickets={', '.join(jira_tickets)}")


def _send_message(base_url: str, session_id: str, message: str, timeout: float) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/chat"
    body = {"session_id": session_id, "message": message}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=body)
        resp.raise_for_status()
        return resp.json()


def _send_message_with_feedback(
    base_url: str,
    session_id: str,
    message: str,
    timeout: float,
) -> dict[str, Any]:
    result: dict[str, Any] | None = None
    error: Exception | None = None

    def _worker() -> None:
        nonlocal result, error
        try:
            result = _send_message(base_url, session_id, message, timeout)
        except Exception as exc:  # noqa: BLE001
            error = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    spinner = ["|", "/", "-", "\\"]
    i = 0
    started = time.monotonic()

    while thread.is_alive():
        elapsed = time.monotonic() - started
        sys.stdout.write(
            f"\rAssistant working {spinner[i % len(spinner)]}  elapsed={elapsed:0.1f}s"
        )
        sys.stdout.flush()
        i += 1
        time.sleep(0.15)

    thread.join()
    elapsed = time.monotonic() - started
    sys.stdout.write(f"\rAssistant done. elapsed={elapsed:0.1f}s{' ' * 24}\n")
    sys.stdout.flush()

    if error is not None:
        raise error
    if result is None:
        raise RuntimeError("No response received from orchestrator.")
    return result


def run_interactive(base_url: str, session_id: str, timeout: float) -> int:
    _print_banner(base_url, session_id)

    while True:
        try:
            user_input = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return 0

        if not user_input:
            continue

        if user_input in {"/quit", "/exit"}:
            print("Exiting.")
            return 0

        if user_input == "/help":
            print("/help    Show commands")
            print("/new     Start a new session id")
            print("/session Print current session id")
            print("/quit    Exit")
            continue

        if user_input == "/new":
            session_id = str(uuid.uuid4())
            print(f"New session: {session_id}")
            continue

        if user_input == "/session":
            print(f"Current session: {session_id}")
            continue

        try:
            payload = _send_message_with_feedback(base_url, session_id, user_input, timeout)
            _print_response(payload)
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error: {exc.response.status_code} {exc.response.text}")
        except Exception as exc:  # noqa: BLE001
            print(f"Request failed: {type(exc).__name__}: {exc}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Terminal chat client for AI Engineering OS")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Orchestrator base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--session-id",
        default=str(uuid.uuid4()),
        help="Session id to continue context across prompts",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--message",
        help="One-shot mode: send a single message and exit",
    )
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="In one-shot mode, print raw JSON response",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.message:
        try:
            payload = _send_message_with_feedback(
                args.base_url,
                args.session_id,
                args.message,
                args.timeout,
            )
            if args.raw_json:
                print(json.dumps(payload, indent=2))
            else:
                _print_response(payload)
            return 0
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error: {exc.response.status_code} {exc.response.text}")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"Request failed: {type(exc).__name__}: {exc}")
            return 1

    return run_interactive(args.base_url, args.session_id, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
