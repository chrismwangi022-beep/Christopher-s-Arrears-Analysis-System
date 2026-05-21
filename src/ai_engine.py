"""
Spread Capital Limited — AI Arrears Intelligence Engine
src/ai_engine.py

Fast, lightweight AI insights engine for Streamlit dashboards.
Optimized for:
- Fast Gemini responses
- Background threading compatibility
- Clean dashboard-ready markdown
- Kenyan microfinance arrears analysis
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import json

import streamlit as st
from google import genai


# ─────────────────────────────────────────────
# MODEL CONFIG
# ─────────────────────────────────────────────

MODEL_NAME = "gemini-2.5-flash"


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
SPREAD CAPITAL LIMITED — ARREARS AI ENGINE

ROLE:
Senior Microfinance Credit Risk Analyst (Kenya)

MODE:
Fast Execution Dashboard Mode

YOUR JOB:
Convert arrears portfolio metrics into:
- short
- precise
- decision-ready insights

DO NOT:
- write reports
- narrate
- explain excessively
- repeat insights

━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Portfolio Snapshot
- Max 2 bullets
- Mention:
  total arrears
  PAR %
  trend
  key affected branches

- End with:
  🟢 Healthy
  🟡 Watchlist
  🔴 Critical

⚠️ Key Risks
- Max 3 bullets
- Risk + impact + branch/officer

🏢 Branch Insights
- Top 3 affected branches only
- Format:
  Branch → issue → trend

👤 Officer Flags
- Only risky officers
- Format:
  Branch → Officer → issue

💡 Recommendations
- Max 3 actions
- Operational only

━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━

- No paragraphs
- No storytelling
- No invented numbers
- Keep every insight short
- Use trend arrows only:
  ↑ worsening
  ↓ improving
  → stable

━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENCY RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━

- ALL money values MUST use:
  KES X,XXX

- NEVER use:
  USD
  EUR
  GBP
  KSh
  Ksh

- Never convert currencies
- If missing, assume KES

━━━━━━━━━━━━━━━━━━━━━━━━━━━
STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Clean banking dashboard style
- Minimal professional emojis only:
  📊 ⚠️ 🏢 👤 💡

- Think:
  executive risk terminal
"""


# ─────────────────────────────────────────────
# METRICS CLEANER
# ─────────────────────────────────────────────

def _clean_metrics(obj: Any) -> Any:
    """
    Clean metrics for JSON serialization.
    Handles:
    - numpy types
    - pandas timestamps
    - nested dicts/lists
    """

    try:
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)

        if isinstance(obj, np.floating):
            return round(float(obj), 2)

    except Exception:
        pass

    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {str(k): _clean_metrics(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_clean_metrics(i) for i in obj]

    return obj


# ─────────────────────────────────────────────
# FORMAT METRICS
# ─────────────────────────────────────────────

def format_metrics(metrics: dict[str, Any]) -> str:

    cleaned = _clean_metrics(metrics)

    cleaned["report_context"] = {
        "company": "Spread Capital Limited",
        "country": "Kenya",
        "currency": "KES",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return json.dumps(cleaned, indent=2)


# ─────────────────────────────────────────────
# MAIN AI FUNCTION
# ─────────────────────────────────────────────

def generate_ai_insights(metrics: dict[str, Any]) -> str:
    """
    Generate AI portfolio insights.

    Returns markdown string.
    Never raises errors to UI.
    """

    try:

        # ── Gemini client ────────────────────
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"]
        )

        # ── Prepare metrics ──────────────────
        metrics_json = format_metrics(metrics)

        # ── User prompt ──────────────────────
        prompt = f"""
Analyse the following arrears portfolio data.

DATA:
```json
{metrics_json}