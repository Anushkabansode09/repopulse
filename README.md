# RepoPulse

**AI agent that evaluates and compares open-source GitHub repository health, so developers can decide whether to depend on them.**

🔗 **Live demo:** https://discerning-emotion-production-fee5.up.railway.app
🔗 **API docs:** https://repopulse-production.up.railway.app/docs

---

## What it does

Developers manually eyeball a repo's activity before adopting it as a dependency — checking last commit date, unresolved issues, stale PRs. RepoPulse automates this into a single, reasoned verdict.

- **Single-repo mode**: paste a GitHub URL, get a health verdict (`healthy` / `at-risk` / `abandoned`) with supporting reasoning
- **Comparison mode**: paste 2-3 repo URLs, get a ranked recommendation on which is the stronger dependency

The verdict isn't a hardcoded rule engine — it's produced by an LLM (Llama 3.1 8B via Groq) reasoning over computed metrics, with structured JSON output and self-correcting retry logic if the model returns malformed output.

## Architecture

```
GitHub REST API
      │
      ▼
github_fetcher.py   → fetches commits, issues, PRs, contributors (with retry logic)
      │
      ▼
health_metrics.py   → computes days-since-commit, issue resolution rate,
                       PR merge rate, active contributor count
      │
      ▼
verdict_agent.py    → LangChain + Groq (Llama 3.1 8B) reasons over metrics,
                       returns structured verdict with self-correction on bad JSON
      │
      ▼
main.py (FastAPI)   → /analyze and /compare endpoints
      │
      ▼
app.py (Streamlit)  → UI, single-repo and comparison views with charts
```

## Tech stack

Python · LangChain · Groq API (Llama 3.1 8B) · GitHub REST API · FastAPI · Streamlit · Docker-ready

## Running locally

```bash
# clone and set up
git clone https://github.com/Anushkabansode09/repopulse.git
cd repopulse
python -m venv venv
venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

# add your keys
# create a .env file with:
# GITHUB_TOKEN=your_github_token
# GROQ_API_KEY=your_groq_key

# run backend (terminal 1)
python main.py

# run frontend (terminal 2)
streamlit run app.py
```

## Key engineering decisions

- **Self-correcting retries**: both the GitHub fetch layer (rate limits, transient errors) and the LLM reasoning layer (malformed JSON) retry before failing, so the pipeline degrades gracefully instead of crashing.
- **Issue/PR separation**: GitHub's `/issues` endpoint includes pull requests by default — filtered out before computing issue resolution rate to avoid double-counting.
- **Structured LLM output**: the reasoning agent is prompted to return strict JSON, validated and retried on failure, so it's safely consumable by the API layer.

## Known limitations

- `active_contributors_90d` is approximated from the last 100 fetched commits (GitHub's contributors endpoint has no date data); may undercount on very high-velocity repos.
- No persistence layer yet — each analysis is stateless.
