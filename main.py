"""
main.py
FastAPI backend for RepoPulse. Exposes a single-repo analysis endpoint.
Comparison mode will be added as /compare once single-repo flow is solid.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from typing import List

from github_fetcher import fetch_repo_data
from health_metrics import calculate_health_metrics
from verdict_agent import get_verdict, get_comparison_verdict

app = FastAPI(title="RepoPulse API", version="0.1.0")


class RepoRequest(BaseModel):
    repo_url: str = Field(..., examples=["https://github.com/psf/requests"])


class AnalyzeResponse(BaseModel):
    metrics: dict
    verdict: dict


class CompareRequest(BaseModel):
    repo_urls: List[str] = Field(..., min_length=2, max_length=3)


class CompareResponse(BaseModel):
    results: list
    comparison: dict


@app.get("/")
def health_check():
    return {"status": "ok", "service": "RepoPulse API"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_repo(request: RepoRequest):
    """
    Full pipeline: fetch -> compute metrics -> reason -> verdict.
    Returns both the raw metrics and the LLM verdict.
    """
    try:
        raw_data = fetch_repo_data(request.repo_url)
    except ValueError as e:
        # e.g. bad URL or repo not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub fetch failed: {e}")

    try:
        metrics = calculate_health_metrics(raw_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics calculation failed: {e}")

    try:
        verdict = get_verdict(metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verdict generation failed: {e}")

    return AnalyzeResponse(metrics=metrics, verdict=verdict)


@app.post("/compare", response_model=CompareResponse)
def compare_repos(request: CompareRequest):
    """
    Runs the fetch -> metrics pipeline on each repo, then asks the LLM
    to rank them and recommend the strongest choice.
    """
    if len(request.repo_urls) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 repo URLs to compare.")

    results = []
    for url in request.repo_urls:
        try:
            raw_data = fetch_repo_data(url)
            metrics = calculate_health_metrics(raw_data)
            results.append({"repo_url": url, "metrics": metrics})
        except ValueError as e:
            raise HTTPException(status_code=404, detail=f"{url}: {e}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"{url}: fetch/metrics failed: {e}")

    try:
        comparison = get_comparison_verdict([r["metrics"] for r in results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison reasoning failed: {e}")

    return CompareResponse(results=results, comparison=comparison)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)