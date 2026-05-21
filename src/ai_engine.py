
"""
Spread Capital Limited — AI Arrears Intelligence Engine
src/ai_engine.py

Fast + lightweight Gemini AI engine for Streamlit dashboards.

Features:
- Fast execution
- Clean dashboard insights
- Kenyan microfinance risk analysis
- Streamlit-safe
- Concise executive intelligence
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

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
Fast Execution Data Interpreter (Executive Terminal)

CORE DIRECTIVE:
Convert arrears portfolio metrics into:
- short
- precise
- decision-ready insights

CRITICAL CONSTRAINTS:
- DO NOT perform any calculations or math.
- DO NOT verify or recompute percentages.
- TRUST all numbers in the provided JSON as absolute truth.
- NEVER invent branch names, officer names, or metrics not present in the data.

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
- Use high-density, professional executive tone.
- Clean banking dashboard style
- Minimal professional emojis only:
  📊 ⚠️ 🏢 👤 💡

- Think:
  executive risk terminal
"""


# ─────────────────────────────────────────────
# CLEAN METRICS
# ─────────────────────────────────────────────

def _clean_metrics(obj: Any) -> Any:
    """
    Cleans metrics for JSON serialization.
    Handles:
    - numpy values
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

    # datetime / pandas timestamp
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    # dictionaries
    if isinstance(obj, dict):
        return {
            str(k): _clean_metrics(v)
            for k, v in obj.items()
        }

    # lists / tuples
    if isinstance(obj, (list, tuple)):
        return [_clean_metrics(i) for i in obj]

    return obj


# ─────────────────────────────────────────────
# FORMAT METRICS
# ─────────────────────────────────────────────

def format_metrics(metrics: dict[str, Any]) -> str:
    """
    Convert metrics dictionary into clean JSON string.
    """

    cleaned = _clean_metrics(metrics)

    cleaned["report_context"] = {
        "company": "Spread Capital Limited",
        "country": "Kenya",
        "currency": "KES",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    return json.dumps(cleaned, indent=2)


# ─────────────────────────────────────────────
# GENERATE AI INSIGHTS
# ─────────────────────────────────────────────

def generate_ai_insights(metrics: dict[str, Any]) -> str:
    """
    Generate AI portfolio insights.

    Parameters
    ----------
    metrics : dict
        Portfolio metrics dictionary

    Returns
    -------
    str
        Markdown dashboard insights
    """

    try:

        # ─────────────────────────────────────
        # Gemini Client
        # ─────────────────────────────────────

        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"]
        )

        # ─────────────────────────────────────
        # Prepare Metrics
        # ─────────────────────────────────────

        metrics_json = format_metrics(metrics)

        # ─────────────────────────────────────
        # Build Prompt
        # ─────────────────────────────────────

        prompt = f"""
INPUT DATA (JSON):
{metrics_json}

TASK:
Interpret the provided JSON data according to your system instructions. 
Provide the structured executive summary now.
"""

        # ─────────────────────────────────────
        # Generate AI Response
        # ─────────────────────────────────────

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                SYSTEM_PROMPT,
                prompt
            ]
        )

        result = response.text.strip()

        # ─────────────────────────────────────
        # Footer
        # ─────────────────────────────────────

        footer = f"""

---

<sub>
🤖 Spread Capital AI Engine · Gemini Flash ·
{datetime.now().strftime("%Y-%m-%d %H:%M")}
</sub>
"""

        return result + footer

    except Exception as e:

        return f"""
> ⚠️ **AI Insights Unavailable**

> {str(e)}

> Portfolio metrics above remain available.
"""