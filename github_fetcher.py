"""
github_fetcher.py
Fetches raw repository health data from the GitHub REST API:
commits, issues, pull requests, and contributors.
"""

import os
import time
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL like https://github.com/owner/repo"""
    cleaned = repo_url.rstrip("/").replace(".git", "")
    parts = cleaned.split("/")
    if len(parts) < 2:
        raise ValueError(f"Could not parse owner/repo from: {repo_url}")
    owner, repo = parts[-2], parts[-1]
    return owner, repo


def _get(url: str, params: dict = None, retries: int = 2):
    """
    Internal GET wrapper with self-correcting retry logic.
    Retries on rate-limit, transient errors, or unexpected empty responses.
    """
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)

            # Handle rate limiting explicitly
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_time - int(time.time()), 1)
                print(f"[retry] Rate limited. Waiting {wait}s before retry...")
                time.sleep(min(wait, 30))  # cap wait for demo purposes
                continue

            if resp.status_code == 404:
                raise ValueError(f"Repo not found (404): {url}")

            resp.raise_for_status()
            return resp.json()

        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt < retries:
                print(f"[retry] Attempt {attempt + 1} failed ({e}). Retrying...")
                time.sleep(1.5 * (attempt + 1))
                continue
            raise

    raise RuntimeError(f"Failed to fetch {url} after {retries + 1} attempts")


def fetch_repo_data(repo_url: str) -> dict:
    """
    Fetch core repo metadata, recent commits, issues, PRs, and contributors.
    Returns a dict of raw data to be processed by calculate_health_metrics.
    """
    owner, repo = parse_repo_url(repo_url)
    base = f"{BASE_URL}/repos/{owner}/{repo}"

    # 1. Repo metadata
    repo_meta = _get(base)

    # 2. Recent commits (last 100, most recent first, default branch)
    commits = _get(f"{base}/commits", params={"per_page": 100})

    # 3. Issues (state=all includes open+closed, excludes PRs is NOT automatic ---
    #    GitHub's /issues endpoint includes PRs, so we filter them out downstream)
    issues = _get(f"{base}/issues", params={"state": "all", "per_page": 100})

    # 4. Pull requests
    pulls = _get(f"{base}/pulls", params={"state": "all", "per_page": 100})

    # 5. Contributors
    contributors = _get(f"{base}/contributors", params={"per_page": 100})

    return {
        "owner": owner,
        "repo": repo,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "meta": repo_meta,
        "commits": commits,
        "issues": issues,
        "pulls": pulls,
        "contributors": contributors,
    }


if __name__ == "__main__":
    # Quick manual test
    test_url = "https://github.com/psf/requests"
    data = fetch_repo_data(test_url)
    print(f"Repo: {data['owner']}/{data['repo']}")
    print(f"Stars: {data['meta'].get('stargazers_count')}")
    print(f"Commits fetched: {len(data['commits'])}")
    print(f"Issues fetched: {len(data['issues'])}")
    print(f"PRs fetched: {len(data['pulls'])}")
    print(f"Contributors fetched: {len(data['contributors'])}")