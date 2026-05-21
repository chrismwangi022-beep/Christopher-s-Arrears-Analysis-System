
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
from .ai_agents import (
    RISK_ANALYST_SYSTEM_PROMPT,
    BRANCH_PERFORMANCE_ANALYST_PROMPT,
    RISK_ANALYSIS_AGENT_PROMPT,
    RECOVERY_STRATEGY_AGENT_PROMPT,
    run_standard_analyst,
    run_risk_agent,
    run_recovery_agent,
    run_branch_agent
)

# ─────────────────────────────────────────────
# MODEL CONFIG
# ─────────────────────────────────────────────

MODEL_NAME = "gemini-2.5-flash"
ORCHESTRATOR_DIRECTIVE = "Interpret the provided JSON data according to your analytical persona. Provide the structured executive summary now."


# Global Client to prevent redundant instantiation
if "genai_client" not in st.session_state:
    st.session_state.genai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def _execute_agent_call(data: dict, system_prompt: str) -> str:
    """Unified production runner for all AI agents."""
    metrics_json = format_metrics(data)
    response = st.session_state.genai_client.models.generate_content(
        model=MODEL_NAME,
        contents=[system_prompt, f"DATA:\n{metrics_json}"]
    )
    return response.text.strip()

def run_multi_agent_analysis(data: dict[str, Any]) -> dict[str, str]:
    """
    Orchestrates specialized interpreters.
    """
    return {
        "executive_summary": _execute_agent_call(data, RISK_ANALYST_SYSTEM_PROMPT),
        "risk": _execute_agent_call(data, RISK_ANALYSIS_AGENT_PROMPT),
        "recovery": _execute_agent_call(data, RECOVERY_STRATEGY_AGENT_PROMPT),
        "branch": _execute_agent_call(data, BRANCH_PERFORMANCE_ANALYST_PROMPT)
    }

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

def generate_ai_insights(metrics: dict[str, Any]) -> dict[str, str]:
    """
    Primary entry point for AI analytics.
    Passes structured metrics unchanged to the orchestrator.
    """
    return run_multi_agent_analysis(metrics)