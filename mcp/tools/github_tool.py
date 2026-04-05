"""GitHub integration tool for the MCP layer."""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx

from mcp.tools.base_tool import BaseTool


class GitHubTool(BaseTool):
    """Interact with GitHub via its REST API.

    Supported actions:
        - ``create_branch`` — create a new branch from a base ref
        - ``push_code``     — create or update a file in the repository
        - ``create_pr``     — open a pull request
        - ``get_pr_status`` — fetch pull-request details and checks
        - ``list_branches`` — list repository branches
    """

    # ------------------------------------------------------------------
    # BaseTool properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "GitHub source-control integration (branches, PRs, code)."

    @property
    def required_params(self) -> dict[str, list[str]]:
        return {
            "create_branch": ["branch_name"],
            "push_code": ["branch", "commit_message"],
            "create_pr": ["title", "head", "base"],
            "get_pr_status": ["pr_number"],
            "list_branches": [],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _config(self) -> tuple[str, str, str]:
        token = os.environ.get("GITHUB_TOKEN", "")
        owner = os.environ.get("GITHUB_OWNER", "")
        repo = os.environ.get("GITHUB_REPO", "")
        return token, owner, repo

    def _client(self) -> httpx.AsyncClient:
        token, _, _ = self._config()
        return httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def _repo_path(self) -> str:
        _, owner, repo = self._config()
        return f"/repos/{owner}/{repo}"

    # ------------------------------------------------------------------
    # Execute dispatcher
    # ------------------------------------------------------------------

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.validate_params(params):
            return self._fail("Invalid or missing parameters for github action.")

        action: str = params["action"]
        try:
            handler = {
                "create_branch": self._create_branch,
                "push_code": self._push_code,
                "create_pr": self._create_pr,
                "get_pr_status": self._get_pr_status,
                "list_branches": self._list_branches,
            }.get(action)

            if handler is None:
                return self._fail(f"Unknown github action: {action}")

            return await handler(params)
        except httpx.HTTPStatusError as exc:
            return self._fail(f"GitHub API error ({exc.response.status_code}): {exc.response.text[:300]}")
        except httpx.RequestError as exc:
            return self._fail(f"GitHub request failed: {str(exc)[:300]}")
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"Unexpected error in github.{action}: {type(exc).__name__}")

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _create_branch(self, params: dict[str, Any]) -> dict[str, Any]:
        branch_name: str = params["branch_name"]
        base_ref: str = params.get("base_ref", "main")
        repo = self._repo_path()

        async with self._client() as client:
            # Resolve the SHA of the base ref.
            ref_resp = await client.get(f"{repo}/git/ref/heads/{base_ref}")
            ref_resp.raise_for_status()
            sha: str = ref_resp.json()["object"]["sha"]

            # Create the new branch ref.
            create_resp = await client.post(
                f"{repo}/git/refs",
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
            )
            create_resp.raise_for_status()
            return self._ok({"branch": branch_name, "sha": sha})

    async def _push_code(self, params: dict[str, Any]) -> dict[str, Any]:
        branch: str = params["branch"]
        message: str = params["commit_message"]
        files: dict[str, str] | None = params.get("files")

        if files is not None:
            if not isinstance(files, dict) or not files:
                return self._fail("For github.push_code, 'files' must be a non-empty {path: content} object.")
            results: list[dict[str, Any]] = []
            for file_path, content in files.items():
                single = await self._push_single_file(
                    file_path=file_path,
                    content=str(content),
                    branch=branch,
                    message=message,
                )
                if not single.get("success"):
                    return single
                if single.get("data"):
                    results.append(single["data"])
            return self._ok({"files": results, "count": len(results)})

        file_path = params.get("file_path")
        content = params.get("content")
        if not file_path or content is None:
            return self._fail("github.push_code requires either ('file_path' + 'content') or 'files'.")

        return await self._push_single_file(
            file_path=str(file_path),
            content=str(content),
            branch=branch,
            message=message,
        )

    async def _push_single_file(
        self,
        *,
        file_path: str,
        content: str,
        branch: str,
        message: str,
    ) -> dict[str, Any]:
        repo = self._repo_path()
        encoded = base64.b64encode(content.encode()).decode()

        async with self._client() as client:
            existing_sha: str | None = None
            check = await client.get(f"{repo}/contents/{file_path}", params={"ref": branch})
            if check.status_code == 200:
                existing_sha = check.json().get("sha")

            payload: dict[str, Any] = {
                "message": message,
                "content": encoded,
                "branch": branch,
            }
            if existing_sha:
                payload["sha"] = existing_sha

            resp = await client.put(f"{repo}/contents/{file_path}", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self._ok({
                "path": file_path,
                "sha": data.get("content", {}).get("sha"),
                "commit_sha": data.get("commit", {}).get("sha"),
            })

    async def _create_pr(self, params: dict[str, Any]) -> dict[str, Any]:
        title: str = params["title"]
        head: str = params["head"]
        base: str = params["base"]
        body: str = params.get("body", "")
        repo = self._repo_path()

        async with self._client() as client:
            resp = await client.post(
                f"{repo}/pulls",
                json={"title": title, "head": head, "base": base, "body": body},
            )
            resp.raise_for_status()
            data = resp.json()
            return self._ok({
                "pr_number": data["number"],
                "url": data["html_url"],
                "state": data["state"],
            })

    async def _get_pr_status(self, params: dict[str, Any]) -> dict[str, Any]:
        pr_number: int = int(params["pr_number"])
        repo = self._repo_path()

        async with self._client() as client:
            resp = await client.get(f"{repo}/pulls/{pr_number}")
            resp.raise_for_status()
            data = resp.json()
            return self._ok({
                "pr_number": data["number"],
                "title": data["title"],
                "state": data["state"],
                "mergeable": data.get("mergeable"),
                "merged": data.get("merged", False),
                "url": data["html_url"],
            })

    async def _list_branches(self, _params: dict[str, Any]) -> dict[str, Any]:
        repo = self._repo_path()

        async with self._client() as client:
            resp = await client.get(f"{repo}/branches", params={"per_page": 100})
            resp.raise_for_status()
            branches = [{"name": b["name"], "sha": b["commit"]["sha"]} for b in resp.json()]
            return self._ok({"branches": branches})
