"""
health_metrics.py
Computes repo health signals from raw GitHub data fetched by github_fetcher.py.
"""

from datetime import datetime, timezone, timedelta


def _parse_iso(ts: str) -> datetime:
    """Parse GitHub's ISO 8601 timestamps into timezone-aware datetimes."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def calculate_health_metrics(raw_data: dict) -> dict:
    """
    Take raw_data from fetch_repo_data() and compute health metrics.
    Returns a dict of computed signals used for the agent's verdict.
    """
    now = datetime.now(timezone.utc)
    commits = raw_data.get("commits", [])
    issues_raw = raw_data.get("issues", [])
    pulls = raw_data.get("pulls", [])
    contributors = raw_data.get("contributors", [])
    meta = raw_data.get("meta", {})

    # --- Days since last commit ---
    days_since_last_commit = None
    if commits:
        last_commit_date = commits[0]["commit"]["committer"]["date"]
        days_since_last_commit = (now - _parse_iso(last_commit_date)).days

    # --- Separate true issues from PRs (GitHub's /issues includes PRs) ---
    true_issues = [i for i in issues_raw if "pull_request" not in i]

    # --- Issue resolution rate ---
    closed_issues = [i for i in true_issues if i["state"] == "closed"]
    issue_resolution_rate = (
        round(len(closed_issues) / len(true_issues) * 100, 1)
        if true_issues else None
    )

    # --- Average time to close an issue (in days), for closed issues only ---
    close_times = []
    for i in closed_issues:
        if i.get("closed_at") and i.get("created_at"):
            delta = _parse_iso(i["closed_at"]) - _parse_iso(i["created_at"])
            close_times.append(delta.total_seconds() / 86400)
    avg_issue_close_days = round(sum(close_times) / len(close_times), 2) if close_times else None
    avg_issue_close_hours = round(avg_issue_close_days * 24, 1) if avg_issue_close_days is not None else None

    # --- PR merge rate ---
    closed_prs = [p for p in pulls if p["state"] == "closed"]
    merged_prs = [p for p in closed_prs if p.get("merged_at")]
    pr_merge_rate = (
        round(len(merged_prs) / len(pulls) * 100, 1)
        if pulls else None
    )

    # --- Active contributors in last 90 days ---
    # contributors endpoint doesn't include dates, so we approximate using
    # unique commit authors within the fetched commit window (last 100 commits).
    cutoff = now - timedelta(days=90)
    recent_authors = set()
    for c in commits:
        commit_date = c.get("commit", {}).get("committer", {}).get("date")
        author_login = (c.get("author") or {}).get("login")
        if commit_date and author_login and _parse_iso(commit_date) >= cutoff:
            recent_authors.add(author_login)
    active_contributors_90d = len(recent_authors)

    return {
        "repo_full_name": f"{raw_data.get('owner')}/{raw_data.get('repo')}",
        "days_since_last_commit": days_since_last_commit,
        "total_issues_sampled": len(true_issues),
        "issue_resolution_rate_pct": issue_resolution_rate,
        "avg_issue_close_days": avg_issue_close_days,
        "avg_issue_close_hours": avg_issue_close_hours,
        "total_prs_sampled": len(pulls),
        "pr_merge_rate_pct": pr_merge_rate,
        "active_contributors_90d": active_contributors_90d,
        "total_contributors_sampled": len(contributors),
        "stars": meta.get("stargazers_count"),
        "open_issues_count": meta.get("open_issues_count"),
        "archived": meta.get("archived", False),
    }


if __name__ == "__main__":
    from github_fetcher import fetch_repo_data

    test_url = "https://github.com/psf/requests"
    raw = fetch_repo_data(test_url)
    metrics = calculate_health_metrics(raw)

    for k, v in metrics.items():
        print(f"{k}: {v}")