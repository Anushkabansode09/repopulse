"""
app.py
Streamlit frontend for RepoPulse — dark theme, neon lime accent, full-width hero.
Calls the FastAPI backend's /analyze endpoint and displays results.
"""

import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="RepoPulse", page_icon="📊", layout="wide")

# ---------- Custom CSS: palette + fonts + layout ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

/* Dark base with blurred gradient hint (navy -> deep green -> lime glow) */
.stApp {
    background:
        radial-gradient(circle at 15% 15%, rgba(0,31,63,0.55) 0%, transparent 45%),
        radial-gradient(circle at 85% 20%, rgba(0,128,76,0.35) 0%, transparent 50%),
        radial-gradient(circle at 50% 90%, rgba(219,230,76,0.12) 0%, transparent 55%),
        #0a0f0a;
    background-attachment: fixed;
}

/* Hero title */
.hero-title {
    font-size: 6rem;
    font-weight: 800;
    color: #DBE64C;
    line-height: 1;
    letter-spacing: -2px;
    margin-bottom: 0;
    text-shadow: 0 0 40px rgba(219,230,76,0.25);
}

.hero-subtitle {
    font-size: 1.3rem;
    color: #A9B4A0;
    font-weight: 400;
    margin-top: 0.3rem;
    margin-bottom: 2.5rem;
}

/* Input field */
.stTextInput input {
    background-color: #10160f;
    color: #F6F7ED;
    border: 1px solid #2a3a2a;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    font-size: 1.05rem;
}
.stTextInput input:focus {
    border-color: #DBE64C;
    box-shadow: 0 0 0 1px #DBE64C;
}

/* Analyze button */
.stButton button {
    background-color: #DBE64C;
    color: #001F3F;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    padding: 0.7rem 2.2rem;
    font-size: 1.05rem;
    transition: transform 0.15s ease;
}
.stButton button:hover {
    transform: scale(1.03);
    background-color: #EEF57A;
    color: #001F3F;
}

/* Verdict banner card */
.verdict-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(219,230,76,0.25);
    border-radius: 16px;
    padding: 2rem 2.2rem;
    margin-top: 2rem;
}

.verdict-title {
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}

.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.metric-card .value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #74C365;
}
.metric-card .label {
    font-size: 0.85rem;
    color: #A9B4A0;
    margin-top: 0.2rem;
}

section[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- Hero ----------
st.markdown('<div class="hero-title">RepoPulse</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">AI-powered health check for open-source GitHub repositories</div>',
    unsafe_allow_html=True,
)

mode = st.radio(
    "Mode",
    ["Single repo", "Compare repos"],
    horizontal=True,
    label_visibility="collapsed",
)

st.write("")

if mode == "Single repo":
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        repo_url = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/owner/repo",
            label_visibility="collapsed",
        )
    with col_btn:
        analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        repo_url_1 = st.text_input("Repo 1", placeholder="https://github.com/owner/repo-a", label_visibility="collapsed")
    with c2:
        repo_url_2 = st.text_input("Repo 2", placeholder="https://github.com/owner/repo-b", label_visibility="collapsed")
    with c3:
        repo_url_3 = st.text_input("Repo 3 (optional)", placeholder="https://github.com/owner/repo-c", label_visibility="collapsed")
    compare_clicked = st.button("Compare", type="primary")

# ---------- Single-repo results ----------
if mode == "Single repo" and analyze_clicked:
    if not repo_url.strip():
        st.warning("Please enter a GitHub repo URL.")
    else:
        with st.spinner("Fetching data and reasoning over repo health..."):
            try:
                resp = requests.post(
                    f"{API_URL}/analyze",
                    json={"repo_url": repo_url.strip()},
                    timeout=30,
                )
            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not reach the RepoPulse API. "
                    "Make sure the backend is running: `python main.py`"
                )
                st.stop()

        if resp.status_code != 200:
            st.error(f"Error ({resp.status_code}): {resp.json().get('detail', 'Unknown error')}")
            st.stop()

        data = resp.json()
        metrics = data["metrics"]
        verdict = data["verdict"]

        verdict_label = verdict.get("verdict", "unknown")
        verdict_styles = {
            "healthy":   {"emoji": "🟢", "color": "#74C365"},
            "at-risk":   {"emoji": "🟡", "color": "#DBE64C"},
            "abandoned": {"emoji": "🔴", "color": "#E85C5C"},
            "unknown":   {"emoji": "⚪", "color": "#A9B4A0"},
        }
        style = verdict_styles.get(verdict_label, verdict_styles["unknown"])

        st.markdown(f"""
        <div class="verdict-card">
            <div class="verdict-title" style="color:{style['color']}">
                {style['emoji']} Verdict: {verdict_label.upper()}
            </div>
            <div style="color:#A9B4A0; margin-bottom:1rem;">
                Confidence: {verdict.get('confidence', 'n/a')}
            </div>
            <div style="font-size:1.05rem; color:#F6F7ED; line-height:1.6;">
                {verdict.get('reasoning', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**⚠️ Concerns**")
            concerns = verdict.get("key_concerns", [])
            st.markdown("\n".join(f"- {c}" for c in concerns) if concerns else "_None flagged_")
        with col2:
            st.markdown("**✅ Strengths**")
            strengths = verdict.get("key_strengths", [])
            st.markdown("\n".join(f"- {s}" for s in strengths) if strengths else "_None flagged_")

        def fmt_pct(val):
            return "N/A" if val is None else f"{val}%"

        def fmt_val(val):
            return "N/A" if val is None else val

        st.markdown("### Raw Metrics")
        m1, m2, m3, m4 = st.columns(4)
        metric_items = [
            (m1, "Days since last commit", fmt_val(metrics.get("days_since_last_commit"))),
            (m2, "Issue resolution rate", fmt_pct(metrics.get("issue_resolution_rate_pct"))),
            (m3, "PR merge rate", fmt_pct(metrics.get("pr_merge_rate_pct"))),
            (m4, "Active contributors (90d)", fmt_val(metrics.get("active_contributors_90d"))),
        ]
        for col, label, value in metric_items:
            col.markdown(f"""
            <div class="metric-card">
                <div class="value">{value}</div>
                <div class="label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("Full metrics JSON"):
            st.json(metrics)

# ---------- Comparison mode results ----------
if mode == "Compare repos" and compare_clicked:
    urls = [u.strip() for u in [repo_url_1, repo_url_2, repo_url_3] if u.strip()]

    if len(urls) < 2:
        st.warning("Enter at least 2 repo URLs to compare.")
    else:
        with st.spinner("Fetching and comparing repos..."):
            try:
                resp = requests.post(
                    f"{API_URL}/compare",
                    json={"repo_urls": urls},
                    timeout=60,
                )
            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not reach the RepoPulse API. "
                    "Make sure the backend is running: `python main.py`"
                )
                st.stop()

        if resp.status_code != 200:
            st.error(f"Error ({resp.status_code}): {resp.json().get('detail', 'Unknown error')}")
            st.stop()

        data = resp.json()
        results = data["results"]
        comparison = data["comparison"]

        st.markdown(f"""
        <div class="verdict-card">
            <div class="verdict-title" style="color:#DBE64C;">
                🏆 Recommended: {comparison.get('recommended_repo', 'N/A')}
            </div>
            <div style="color:#A9B4A0; margin-bottom:1rem;">
                Confidence: {comparison.get('confidence', 'n/a')}
            </div>
            <div style="font-size:1.05rem; color:#F6F7ED; line-height:1.6;">
                {comparison.get('reasoning', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        ranking = comparison.get("ranking", [])
        if ranking:
            st.markdown("**Ranking**")
            st.markdown("\n".join(f"{i+1}. {r}" for i, r in enumerate(ranking)))

        st.markdown("### Side-by-side metrics")

        rows = []
        for r in results:
            m = r["metrics"]
            rows.append({
                "Repo": m.get("repo_full_name"),
                "Days since last commit": m.get("days_since_last_commit"),
                "Issue resolution %": m.get("issue_resolution_rate_pct"),
                "PR merge %": m.get("pr_merge_rate_pct"),
                "Active contributors (90d)": m.get("active_contributors_90d"),
                "Stars": m.get("stars"),
            })
        df = pd.DataFrame(rows).set_index("Repo")
        st.dataframe(df, use_container_width=True)

        st.markdown("### Comparison charts")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.caption("Issue resolution rate & PR merge rate (%)")
            st.bar_chart(df[["Issue resolution %", "PR merge %"]])
        with chart_col2:
            st.caption("Active contributors (last 90 days)")
            st.bar_chart(df[["Active contributors (90d)"]])