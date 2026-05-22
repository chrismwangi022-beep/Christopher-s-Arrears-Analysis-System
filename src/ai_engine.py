
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
import time
import random
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

MODEL_FALLBACK_ORDER = ["gemini-2.0-flash", "gemini-2.0-flash", "gemini-2.0-flash"]
ORCHESTRATOR_DIRECTIVE = "Interpret the provided JSON data according to your analytical persona. Provide the structured executive summary now."
MAX_RETRIES = 2
INITIAL_BACKOFF = 2  # seconds

def generate_local_insights(metrics: dict[str, Any]) -> dict[str, str]:
    """
    Deterministic rule-based engine that mimics AI output style.
    Ensures zero-failure UX when API quotas are exhausted.
    """
    total_arrears = metrics.get("total_arrears", 0)
    par_pct = metrics.get("par_percentage", 0)
    accounts = metrics.get("accounts_in_arrears", 0)
    avg_days = metrics.get("average_days_past_due", 0)
    branch_summary = metrics.get("top_branch_arrears", {})
    officer_summary = metrics.get("officer_summary", {})

    # 1. Deterministic Status Logic
    status = "🟢 Healthy"
    if par_pct >= 15 or avg_days > 60:
        status = "🔴 Critical"
    elif par_pct >= 5 or avg_days > 30:
        status = "🟡 Watchlist"

    # 2. Portfolio Snapshot (Mimicking Executive Summary)
    summary = (
        "📊 Portfolio Snapshot (Local Analysis Mode)\n"
        f"- Portfolio exposure is **KES {total_arrears:,.2f}** with **{accounts:,}** active defaulters.\n"
        f"- PAR is currently **{par_pct:.2f}%** with an aging average of **{avg_days:.1f} days**.\n\n"
        f"- **Current Outlook:** {status}"
    )

    # 3. Risk Drivers
    risks = "⚠️ Key Risks\n"
    if par_pct > 10:
        risks += f"- **High PAR**: Systemic risk detected with {par_pct}% of principal in arrears.\n"
    if avg_days > 45:
        risks += f"- **Stagnant Recovery**: High average days ({avg_days}) indicates slowing collection velocity.\n"
    if not any([par_pct > 10, avg_days > 45]):
        risks += "- No high-level systemic risks identified in the current selection.\n"

    # 4. Branch & Officer Insights
    branch_insights = "🏢 Branch Insights\n"
    top_branches = list(branch_summary.keys())[:3]
    if top_branches:
        for b in top_branches:
            branch_insights += f"- {b.title()} → Concentration of KES {branch_summary[b]:,.0f}\n"
    else:
        branch_insights += "- No branch concentration data available.\n"
        
    branch_insights += "\n👤 Officer Flags\n"
    top_officers = list(officer_summary.keys())[:3]
    if top_officers:
        for off in top_officers:
            branch_insights += f"- {off.title()} → Managing KES {officer_summary[off]:,.0f} in arrears\n"

    # 5. Recommendations
    rec = "💡 Recommendations\n"
    if par_pct > 12:
        rec += "- **Freeze**: Halt new disbursements for the worst-performing branches.\n"
        rec += "- **Escalate**: Trigger immediate legal demand letters for accounts > 90 days.\n"
    elif par_pct > 5:
        rec += "- **Intensity**: Increase frequency of field visits to 'Warning' category clients.\n"
        rec += "- **Review**: Audit payment plans for top 10 defaulters.\n"
    else:
        rec += "- **Monitor**: Continue low-touch SMS and automated call reminders.\n"

    return {
        "executive_summary": summary,
        "risk": risks.strip(),
        "recovery": rec.strip(),
        "branch": branch_insights.strip()
    }

def _execute_agent_call(data: dict, system_prompt: str) -> str:
    """
    Unified production runner for all AI agents with model fallback and exponential backoff.
    """
    # Initialize client inside the session context to avoid AttributeErrors during module import
    if "genai_client" not in st.session_state:
        st.session_state.genai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    metrics_json = format_metrics(data)
    last_error = ""

    for model_name in MODEL_FALLBACK_ORDER:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = st.session_state.genai_client.models.generate_content(
                    model=model_name,
                    contents=[system_prompt, f"DATA:\n{metrics_json}"]
                )
                if response and response.text:
                    return response.text.strip()
                
            except Exception as e:
                err_msg = str(e).lower()
                last_error = str(e)
                
                # Check for quota or rate limit errors
                is_quota_issue = any(x in err_msg for x in ["429", "resource_exhausted", "quota exceeded"])
                
                if is_quota_issue:
                    if attempt < MAX_RETRIES:
                        # Exponential backoff with jitter
                        sleep_time = (INITIAL_BACKOFF ** attempt) + random.uniform(0, 1)
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Max retries reached for this model, fall back to next model
                        break
                else:
                    # Unrecoverable error (e.g. auth, malformed prompt), stop immediately
                    return f"⚠️ Analysis Error: {last_error}"

    return f"🛡️ AI Service Temporarily Busy: The system encountered a high load. Please try again in a few moments. (Technical Detail: {last_error})"


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

def get_ai_health_state() -> dict[str, Any]:
    """Initializes and returns the AI health tracking state for the dashboard."""
    if "ai_health" not in st.session_state:
        has_key = "GEMINI_API_KEY" in st.secrets
        st.session_state.ai_health = {
            "status": "Online" if has_key else "Offline",
            "is_local": not has_key,
            "last_success": "N/A",
            "model": "gemini-2.0-flash" if has_key else "Deterministic Engine",
            "error": "" if has_key else "Missing API Credentials (GEMINI_API_KEY)"
        }
    return st.session_state.ai_health

@st.cache_data(ttl=600, show_spinner=False)
def generate_ai_insights(metrics: dict[str, Any]) -> dict[str, str]:
    """
    Primary entry point for AI analytics.
    Implements a hybrid intelligence strategy with deterministic fallback.
    """
    try:
        # Early exit if API key is missing
        if not st.secrets.get("GEMINI_API_KEY"):
            return generate_local_insights(metrics)

        # Attempt multi-agent AI analysis
        results = run_multi_agent_analysis(metrics)
        
        # Detection: If any agent returns an error signature, trigger the fallback engine
        # to ensure the UI remains clean and consistent.
        if any(v.startswith(("⚠️", "🛡️")) for v in results.values()):
            return generate_local_insights(metrics)
            
        return results
        
    except Exception:
        # Absolute safety net: Switch to local insights on any failure
        return generate_local_insights(metrics)