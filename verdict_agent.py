"""
verdict_agent.py
Takes computed health metrics and produces a plain-English verdict
(healthy / at-risk / abandoned) with supporting reasoning, using an LLM.
"""

import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

VERDICT_SYSTEM_PROMPT = """You are RepoPulse, an expert at evaluating open-source repository health for developers deciding whether to depend on a library.

You will be given computed metrics for a GitHub repository. Reason over them like an experienced engineer would, then respond with STRICT JSON only, no markdown, no preamble, in this exact shape:

{
  "verdict": "healthy" | "at-risk" | "abandoned",
  "confidence": "high" | "medium" | "low",
  "reasoning": "2-4 sentences explaining the verdict, referencing specific numbers",
  "key_concerns": ["short phrase", "short phrase"],
  "key_strengths": ["short phrase", "short phrase"]
}

Guidelines for judgment (use as heuristics, not rigid rules):
- days_since_last_commit > 180 with low active_contributors_90d strongly suggests abandonment
- archived=true means automatically "abandoned" regardless of other metrics
- issue_resolution_rate_pct and pr_merge_rate_pct below ~30% suggest maintainer bandwidth problems (at-risk)
- active_contributors_90d of 0-1 on a repo with any meaningful userbase (stars > 100) is a red flag
- High stars alone does NOT mean healthy — a popular but abandoned repo is still abandoned
- Weigh recency of commits and active contributors most heavily; resolution/merge rates second
- Small sample sizes (e.g. total_issues_sampled < 10) should lower your confidence, not your verdict certainty in the text
"""


def get_verdict(metrics: dict) -> dict:
    """
    Send computed metrics to the LLM and get back a structured verdict.
    Includes basic self-correction: if the model returns invalid JSON,
    retry once with a stricter reminder.
    """
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model="llama-3.1-8b-instant",
        temperature=0.2,
    )

    user_prompt = f"Here are the computed health metrics for a repository:\n\n{json.dumps(metrics, indent=2)}\n\nRespond with the JSON verdict only."

    messages = [
        ("system", VERDICT_SYSTEM_PROMPT),
        ("human", user_prompt),
    ]

    response = llm.invoke(messages)
    raw_text = response.content.strip()

    verdict = _try_parse_json(raw_text)
    if verdict is not None:
        return verdict

    # Self-correction retry: remind the model to strictly output JSON
    retry_messages = messages + [
        ("human", "That was not valid JSON. Respond again with ONLY the raw JSON object, no markdown fences, no extra text.")
    ]
    response2 = llm.invoke(retry_messages)
    raw_text2 = response2.content.strip()
    verdict2 = _try_parse_json(raw_text2)

    if verdict2 is not None:
        return verdict2

    # Final fallback: return a safe default so the pipeline never crashes
    return {
        "verdict": "unknown",
        "confidence": "low",
        "reasoning": "The reasoning model failed to return a parseable verdict after retry.",
        "key_concerns": ["LLM output parsing failure"],
        "key_strengths": [],
    }


def _try_parse_json(text: str):
    """Attempt to parse JSON, stripping common markdown fence wrappers."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


COMPARISON_SYSTEM_PROMPT = """You are RepoPulse, an expert at comparing open-source repositories to help a developer pick the stronger dependency.

You will be given computed health metrics for 2-3 repositories. Compare them and respond with STRICT JSON only, no markdown, no preamble, in this exact shape:

{
  "recommended_repo": "owner/repo",
  "confidence": "high" | "medium" | "low",
  "reasoning": "3-5 sentences explaining why this repo is the stronger choice, referencing specific numbers from multiple repos being compared",
  "ranking": ["owner/repo (best)", "owner/repo", "owner/repo (worst)"]
}

Guidelines:
- Weigh recency of commits and active contributors most heavily
- A repo with more stars is not automatically better if it's less actively maintained
- Call out meaningful trade-offs (e.g. "repo A is more active but repo B resolves issues faster")
- If metrics are missing (null) for a repo due to small sample size, factor that into confidence, not into penalizing the repo unfairly
"""


def get_comparison_verdict(metrics_list: list[dict]) -> dict:
    """
    Send computed metrics for 2-3 repos to the LLM and get a ranked recommendation.
    Includes the same self-correction retry pattern as get_verdict.
    """
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model="llama-3.1-8b-instant",
        temperature=0.2,
    )

    user_prompt = (
        f"Here are the computed health metrics for {len(metrics_list)} repositories:\n\n"
        f"{json.dumps(metrics_list, indent=2)}\n\n"
        f"Respond with the JSON comparison verdict only."
    )

    messages = [
        ("system", COMPARISON_SYSTEM_PROMPT),
        ("human", user_prompt),
    ]

    response = llm.invoke(messages)
    raw_text = response.content.strip()

    result = _try_parse_json(raw_text)
    if result is not None:
        return result

    retry_messages = messages + [
        ("human", "That was not valid JSON. Respond again with ONLY the raw JSON object, no markdown fences, no extra text.")
    ]
    response2 = llm.invoke(retry_messages)
    result2 = _try_parse_json(response2.content.strip())

    if result2 is not None:
        return result2

    return {
        "recommended_repo": metrics_list[0].get("repo_full_name", "unknown") if metrics_list else "unknown",
        "confidence": "low",
        "reasoning": "The reasoning model failed to return a parseable comparison after retry. Defaulting to first repo.",
        "ranking": [m.get("repo_full_name", "unknown") for m in metrics_list],
    }


if __name__ == "__main__":
    from github_fetcher import fetch_repo_data
    from health_metrics import calculate_health_metrics

    test_url = "https://github.com/psf/requests"
    raw = fetch_repo_data(test_url)
    metrics = calculate_health_metrics(raw)

    print("--- METRICS ---")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    print("\n--- VERDICT ---")
    verdict = get_verdict(metrics)
    print(json.dumps(verdict, indent=2))