
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
import pandas as pd
from datetime import datetime, timedelta
from typing import Any

import streamlit as st

# Safe Import Guard for OpenAI / OpenRouter
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .ai_agents import (
    RISK_ANALYST_SYSTEM_PROMPT,
    BRANCH_PERFORMANCE_ANALYST_PROMPT,
    RISK_ANALYSIS_AGENT_PROMPT,
    RECOVERY_STRATEGY_AGENT_PROMPT,
    RECOVERY_MANAGER_PROMPT,
)

# ─────────────────────────────────────────────
# MODEL CONFIG
# ─────────────────────────────────────────────

MODEL_NAME = "deepseek/deepseek-chat"
ORCHESTRATOR_DIRECTIVE = "Interpret the provided JSON data according to your analytical persona. Provide the structured executive summary now."
MAX_RETRIES = 2
INITIAL_BACKOFF = 2  # seconds

SYSTEM_PROMPT = """
You are a senior microfinance risk analyst.
Generate concise portfolio insights, branch analysis, officer flags, and recommendations.
Keep executive style. No storytelling.
"""

def generate_local_insights(metrics: dict[str, Any]) -> dict[str, str]:
    """
    Deterministic rule-based engine that mimics AI output style.
    Ensures zero-failure UX when API quotas are exhausted.
    """
    total_arrears = metrics.get("total_arrears", 0)
    par_pct = metrics.get("par_percentage", 0)
    accounts = metrics.get("accounts_in_arrears", 0)
    avg_days = metrics.get("average_days_past_due", 0)
    branch_risk_list = metrics.get("branch_risk_summary", [])
    officer_summary = metrics.get("officer_summary", {})

    # 1. Deterministic Status Logic
    status = "🟢 Healthy"
    if par_pct >= 20 or avg_days > 60:
        status = "🔴 Critical"
    elif par_pct >= 10:
        status = "🟠 High Risk"
    elif par_pct >= 5 or avg_days > 30:
        status = "🟡 Watchlist"

    # 2. Portfolio Snapshot (Mimicking Executive Summary)
    summary = (
        "📊 Portfolio Snapshot (Local Analysis Mode)\n"
        f"- Portfolio exposure is **KES {total_arrears:,.0f}** with **{accounts:,}** active defaulters.\n"
        f"- PAR is currently **{par_pct:.1f}%** with an aging average of **{avg_days:.1f} days**.\n\n"
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

    # 4. Branch Portfolio Performance (Ratio-Based)
    branch_insights = "🏢 Branch Portfolio Analysis\n"
    if branch_risk_list:
        # Performance Ranking (Portfolio Quality)
        sorted_branches = sorted(branch_risk_list, key=lambda x: x['Risk_Ratio'], reverse=True)
        worst = sorted_branches[0]
        best = sorted_branches[-1]

        branch_insights += "**A. Relative Portfolio Performance (Ranking)**\n"
        branch_insights += f"- **Highest Risk Branch (Relative):** {worst['Branch'].title()} ({worst['Risk_Ratio']:.1%}) — *{worst['Classification']}*\n"
        branch_insights += f"- **Lowest Risk Branch (Relative):** {best['Branch'].title()} ({best['Risk_Ratio']:.1%}) — *{best['Classification']}*\n\n"
        
        # Absolute status and concentration
        branch_insights += "**B. Absolute Health Status & Concentration**\n"
        top_exposure = sorted(branch_risk_list, key=lambda x: x['Arrears'], reverse=True)[0]
        branch_insights += f"- **Primary Exposure Hub:** {top_exposure['Branch'].title()} holds **{top_exposure['Portfolio_Contribution']:.1%}** of total arrears volume.\n"

        # Identification of critical branches
        critical_branches = [f"{b['Branch'].title()} ({b['Trend']})" for b in sorted_branches if b['Risk_Ratio'] >= 0.20]
        if critical_branches:
            branch_insights += f"- **Elevated Delinquency Risk:** {', '.join(critical_branches)} exceed 20% critical threshold.\n"
    else:
        branch_insights += "- No branch risk data available for the current selection.\n"
        
    branch_insights += "\n👤 Officer-Level Recovery Actions\n"
    # Required Fix: Generate actions based ONLY on officer's specific portfolio
    # This prevents cross-branch contamination (e.g. Embu officer receiving Serem tasks)
    processed_officers = 0
    for off_name, stats in officer_summary.items():
        if processed_officers >= 5: break # limit to top 5 risk-heavy officers
        
        # Safeguards: Skip empty portfolios or invalid branch assignments
        arrears = stats.get('Arrears', 0) if isinstance(stats, dict) else stats
        branch = stats.get('Branch', 'Unassigned') if isinstance(stats, dict) else "Assigned Branch"
        days = stats.get('Avg_Days', avg_days) if isinstance(stats, dict) else avg_days
        
        if arrears <= 0 or not branch or branch in ["Unassigned", "NaN"]:
            continue
            
        # Quality: Use officer-specific delinquency patterns and recovery urgency
        if days > 180:
            action = f"Prioritize recovery follow-up on accounts above 180 days within your {branch.title()} portfolio, particularly high-balance delinquent accounts showing prolonged inactivity."
        elif days > 90:
            action = f"Initiate immediate legal demand procedures and asset recovery protocols for accounts in {branch.title()} exceeding 90 days."
        elif days > 30:
            action = f"Intensify field visits to {branch.title()} clients in the 31-90 day bucket to prevent further aging into loss categories."
        else:
            action = f"Maintain routine collection frequency and automated SMS reminders for the early-stage {branch.title()} portfolio."
            
        branch_insights += f"- **{off_name.title()} ({branch.title()}):** {action}\n"
        processed_officers += 1

    if processed_officers == 0:
        branch_insights += "- No specific officer-level actions flagged for this selection.\n"

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
    if not HAS_OPENAI:
        # Return an error signature that triggers generate_local_insights
        return "⚠️ OpenAI/OpenRouter library missing from requirements.txt."

    if "ai_client" not in st.session_state:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "⚠️ Missing OPENROUTER_API_KEY configuration."
            
        try:
            st.session_state.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        except Exception as e:
            return f"⚠️ API Initialization Error: {str(e)}"

    metrics_json = format_metrics(data)

    try:
        response = st.session_state.ai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"DATA:\n{metrics_json}"}
            ],
            temperature=0.3,
            max_tokens=700
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        return f"🛡️ AI Service Temporarily Busy: {str(e)}"


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

    # Return early for standard Python primitives
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj

    try:
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)

        if isinstance(obj, np.floating):
            return round(float(obj), 2)

    except Exception:
        pass

    # datetime / pandas timestamp - Using getattr to avoid static analysis warnings
    iso_method = getattr(obj, "isoformat", None)
    if iso_method and callable(iso_method):
        return iso_method()

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
        # Pre-flight check: Key must exist AND library must be installed
        is_functional = HAS_OPENAI and st.secrets.get("OPENROUTER_API_KEY") is not None
        st.session_state.ai_health = {
            "status": "Online" if is_functional else "Offline",
            "is_local": not is_functional,
            "last_success": "N/A",
            "model": "DeepSeek (OpenRouter)" if is_functional else "Deterministic Engine",
            "error": "" if is_functional else ("Library missing" if not HAS_OPENAI else "Missing OPENROUTER_API_KEY")
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
        if not HAS_OPENAI or not st.secrets.get("OPENROUTER_API_KEY"):
            return generate_local_insights(metrics)

        # Attempt multi-agent AI analysis
        results = run_multi_agent_analysis(metrics)

        # Append the DeepSeek footer to the executive summary
        footer = f"\n\n---\n📈 AI Analytics Engine · DeepSeek AI · Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if "executive_summary" in results and not results["executive_summary"].startswith(("⚠️", "🛡️")):
            results["executive_summary"] += footer
        
        # Detection: If any agent returns an error signature, trigger the fallback engine
        # to ensure the UI remains clean and consistent.
        if any(v.startswith(("⚠️", "🛡️")) for v in results.values()):
            return generate_local_insights(metrics)
            
        return results
        
    except Exception:
        # Absolute safety net: Switch to local insights on any failure
        return generate_local_insights(metrics)

@st.cache_data(ttl=3600, show_spinner="🚨 Preparing Weekly Recovery Intelligence...")
def generate_weekly_recovery_reports(df: pd.DataFrame) -> dict[str, str]:
    """
    Pre-generates aggressive recovery reports for all branches.
    Analyzes dynamic weekly windows (Monday to Current Day).
    """
    if df.empty:
        return {}

    from .calculations import find_column_case_insensitive
    b_col = find_column_case_insensitive(df, 'Branch') or 'Branch'
    a_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    d_col = find_column_case_insensitive(df, 'Report_Date') or 'Report_Date'

    if d_col not in df.columns:
        return {}

    # 1. Setup Time Window (Monday to Now)
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 2. Process all branches
    reports = {}
    unique_branches = df[b_col].dropna().unique()

    for branch in unique_branches:
        branch_df = df[df[b_col] == branch].copy()
        branch_df[d_col] = pd.to_datetime(branch_df[d_col])
        
        # Weekly Window Data
        this_week = branch_df[branch_df[d_col] >= pd.Timestamp(monday)]
        if this_week.empty:
            continue

        daily_totals = this_week.groupby(d_col)[a_col].sum().sort_index()
        
        # Metric Calculations
        opening_val = float(daily_totals.iloc[0])
        closing_val = float(daily_totals.iloc[-1])
        peak_val = float(daily_totals.max())
        peak_date = daily_totals.idxmax().strftime('%Y-%m-%d')
        net_move = closing_val - opening_val
        
        # Daily movement analysis
        diffs = daily_totals.diff().fillna(0)
        max_spike = float(diffs.max())
        max_recovery = float(abs(diffs.min())) if diffs.min() < 0 else 0.0

        metrics_bundle = {
            "branch": str(branch),
            "week_range": f"{monday.strftime('%b %d')} - {now.strftime('%b %d, %Y')}",
            "opening_arrears": opening_val,
            "closing_arrears": closing_val,
            "peak_arrears": peak_val,
            "peak_date": peak_date,
            "net_movement": net_move,
            "largest_spike": max_spike,
            "strongest_recovery": max_recovery,
            "daily_history": daily_totals.to_dict()
        }

        # 3. Call Recovery Manager AI
        reports[branch] = _execute_recovery_manager_call(metrics_bundle)

    return reports

def _execute_recovery_manager_call(data: dict) -> str:
    """Private runner for the Recovery Manager Agent."""
    if not HAS_OPENAI or not st.secrets.get("OPENROUTER_API_KEY"):
        return f"🚨 [LOCAL FALLBACK] Recovery Report for {data['branch']}: Week movement is {data['net_movement']:,.0f}. Immediate field action required."

    if "ai_client" not in st.session_state:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if not api_key:
            return "⚠️ Missing API Key"
            
        try:
            st.session_state.ai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        except:
            return "⚠️ Connection Error"

    try:
        # Using deepseek-chat for aggressive reasoning
        response = st.session_state.ai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": RECOVERY_MANAGER_PROMPT},
                {"role": "user", "content": f"WEEKLY METRICS:\n{json.dumps(data, indent=2)}"}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        return f"🛡️ Recovery AI Busy: {str(e)}"