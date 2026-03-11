import asyncio
import json
import os
from typing import Optional
from urllib import error, request


def _get_client():
    from github import Github

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not set")
    return Github(token)


async def wait_for_ci(full_name: str, commit_sha: str, timeout: int = 120) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"status": "skipped", "reason": "no_token"}

    poll_interval = 10
    elapsed = 0

    while elapsed < timeout:
        try:
            req = request.Request(
                url=f"https://api.github.com/repos/{full_name}/commits/{commit_sha}/check-runs",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            check_runs = data.get("check_runs", [])
            if not check_runs:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                continue

            all_complete = all(cr.get("status") == "completed" for cr in check_runs)
            if not all_complete:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                continue

            all_passed = all(cr.get("conclusion") in ("success", "skipped", "neutral") for cr in check_runs)
            failed = [cr["name"] for cr in check_runs if cr.get("conclusion") not in ("success", "skipped", "neutral")]
            run_url = check_runs[0].get("details_url", "") if check_runs else ""

            return {
                "status": "passed" if all_passed else "failed",
                "url": run_url,
                "total": len(check_runs),
                "failed_jobs": failed,
            }

        except (error.HTTPError, error.URLError, json.JSONDecodeError):
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    return {"status": "timeout", "reason": f"CI not complete within {timeout}s"}


def _github_api_get(path: str, token: str) -> dict | list | None:
    req = request.Request(
        url=f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (error.HTTPError, error.URLError, json.JSONDecodeError):
        return None


def _get_job_log(full_name: str, job_id: int, token: str) -> str:
    class _NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    req = request.Request(
        url=f"https://api.github.com/repos/{full_name}/actions/jobs/{job_id}/logs",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        opener = request.build_opener(_NoRedirect)
        with opener.open(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return raw[-3000:]
    except error.HTTPError as e:
        location = e.headers.get("Location")
        if e.code in (301, 302, 303, 307, 308) and location:
            try:
                redirected_req = request.Request(location, headers={"User-Agent": "vibeDeploy-ci-log/1.0"})
                with request.urlopen(redirected_req, timeout=20) as redirected_resp:
                    raw = redirected_resp.read().decode("utf-8", errors="replace")
                    return raw[-3000:]
            except (error.HTTPError, error.URLError):
                return ""
        return ""
    except error.URLError:
        return ""


async def get_ci_failure_logs(full_name: str, commit_sha: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return ""

    runs = _github_api_get(f"/repos/{full_name}/actions/runs?head_sha={commit_sha}", token)
    if not runs or not isinstance(runs, dict) or not runs.get("workflow_runs"):
        return ""

    run_id = runs["workflow_runs"][0]["id"]

    jobs_data = _github_api_get(f"/repos/{full_name}/actions/runs/{run_id}/jobs", token)
    if not jobs_data or not isinstance(jobs_data, dict):
        return ""

    logs_parts: list[str] = []
    for job in jobs_data.get("jobs", []):
        if job.get("conclusion") != "failure":
            continue

        job_name = job["name"]
        failed_steps = [s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"]
        job_log = _get_job_log(full_name, job["id"], token)

        logs_parts.append(f"=== Job '{job_name}' FAILED ===")
        logs_parts.append(f"Failed steps: {', '.join(failed_steps)}")
        if job_log:
            logs_parts.append(job_log)

    return "\n".join(logs_parts)


async def create_github_repo(
    name: str,
    files: dict[str, str],
    description: str = "",
    private: bool = False,
    org: Optional[str] = None,
) -> dict:
    from github import GithubException

    try:
        gh = _get_client()

        if org:
            owner = gh.get_organization(org)
        else:
            owner = gh.get_user()

        repo = owner.create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=True,
            license_template="mit",
        )

        initial_push = {"status": "skipped", "commit_sha": ""}
        if files:
            initial_push = await push_files(
                {"full_name": repo.full_name},
                files,
                commit_message="Initial app code generated by vibeDeploy",
                branch=repo.default_branch,
            )
            if initial_push.get("status") != "pushed":
                try:
                    repo.delete()
                except Exception:
                    pass
                return {
                    "url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "full_name": repo.full_name,
                    "status": "error",
                    "error": initial_push.get("error", "Initial code push failed"),
                }

        return {
            "url": repo.html_url,
            "clone_url": repo.clone_url,
            "full_name": repo.full_name,
            "status": "created",
            "initial_commit_sha": initial_push.get("commit_sha", ""),
        }

    except GithubException as e:
        return {"url": "", "status": "error", "error": f"GitHub API: {e.data.get('message', str(e))}"}
    except ValueError as e:
        return {"url": "", "status": "error", "error": str(e)}


async def push_files(
    repo: dict,
    files: dict[str, str],
    commit_message: str = "Update from vibeDeploy",
    branch: str | None = None,
) -> dict:
    from github import GithubException, InputGitTreeElement

    try:
        gh = _get_client()
        gh_repo = gh.get_repo(repo["full_name"])

        if branch is None:
            branch = gh_repo.default_branch

        ref = gh_repo.get_git_ref(f"heads/{branch}")
        base_sha = ref.object.sha
        base_tree = gh_repo.get_git_tree(base_sha)

        tree_elements = []
        for path, content in files.items():
            blob = gh_repo.create_git_blob(content, "utf-8")
            tree_elements.append(
                InputGitTreeElement(
                    path=path,
                    mode="100644",
                    type="blob",
                    sha=blob.sha,
                )
            )

        new_tree = gh_repo.create_git_tree(tree_elements, base_tree)
        commit = gh_repo.create_git_commit(
            message=commit_message,
            tree=new_tree,
            parents=[gh_repo.get_git_commit(base_sha)],
        )
        ref.edit(commit.sha)

        return {
            "status": "pushed",
            "commit_sha": commit.sha,
            "files_count": len(files),
        }

    except GithubException as e:
        return {"status": "error", "error": f"GitHub API: {e.data.get('message', str(e))}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
