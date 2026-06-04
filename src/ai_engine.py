
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
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any

import streamlit as st

# Safe Import Guard for Google Gemini SDK
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from .gemini_client import generate_gemini_response
from .forecasting import forecast_arrears_30d, get_forecast_by_group

from .ai_agents import (
    RISK_ANALYST_SYSTEM_PROMPT,
    BRANCH_PERFORMANCE_ANALYST_PROMPT,
    RISK_ANALYSIS_AGENT_PROMPT,
    RECOVERY_STRATEGY_AGENT_PROMPT,
    FORECAST_AGENT_PROMPT,
    RECOVERY_MANAGER_PROMPT,
)

# ─────────────────────────────────────────────
# MODEL CONFIG
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior microfinance risk analyst.
Generate concise portfolio insights, branch analysis, officer flags, and recommendations.
Keep executive style. No storytelling.
"""

def build_ai_context(df_filtered: pd.DataFrame, top_n: int = 10) -> dict[str, Any]:
    """
    Redesigns the AI input pipeline to provide structured portfolio intelligence.
    Aggregates essential segments while providing row-level visibility into outliers.
    """
    if df_filtered.empty:
        return {}

    # 1. Row-Level Data Sampling (Lightweight "Texture")
    # We select essential columns and sample to avoid token bloat
    essential_cols = ['Branch', 'Product', 'Loan_Officer', 'Days', 'Arrears', 'Aging_Bucket']
    cols_present = [c for c in essential_cols if c in df_filtered.columns]
    
    # Take a representative sample (Top 15 by Arrears + 15 random for variety)
    top_rows = df_filtered.nlargest(15, 'Arrears')[cols_present]
    random_rows = df_filtered.sample(n=min(len(df_filtered), 15))[cols_present]
    sample_data = pd.concat([top_rows, random_rows]).drop_duplicates().to_dict(orient='records')

    # 2. Segmented Breakdowns
    branch_breakdown = df_filtered.groupby('Branch')['Arrears'].sum().sort_values(ascending=False).to_dict()
    product_breakdown = df_filtered.groupby('Product')['Arrears'].sum().sort_values(ascending=False).to_dict()
    
    # 3. Aging Distribution
    aging_dist = df_filtered.groupby('Aging_Bucket').agg({
        'Arrears': 'sum',
        'AccountID': 'count'
    }).rename(columns={'AccountID': 'Count'}).to_dict(orient='index')

    # 4. Top Risky Outliers (High Exposure Accounts)
    top_risky = df_filtered.nlargest(top_n, 'Arrears')[cols_present].to_dict(orient='records')

    # 5. Officer Performance Summary
    officer_perf = df_filtered.groupby('Loan_Officer').agg({
        'Arrears': 'sum',
        'Days': 'mean'
    }).sort_values('Arrears', ascending=False).head(5).to_dict(orient='index')

    # 6. Predictive Forecasting Data
    overall_forecast = forecast_arrears_30d(df_filtered)

    context = {
        "metadata": {
            "total_records_processed": len(df_filtered),
            "currency": "KES",
            "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        },
        "portfolio_segments": {
            "by_branch": branch_breakdown,
            "by_product": product_breakdown,
            "aging_distribution": aging_dist
        },
        "forecasting_30d": overall_forecast,
        "high_risk_outliers": top_risky,
        "officer_performance_top_5": officer_perf,
        "data_samples": sample_data
    }

    return _clean_metrics(context)

def generate_local_insights(metrics: dict[str, Any]) -> dict[str, str]:
    """
    Deterministic rule-based engine that mimics AI output style.
    Ensures zero-failure UX when API quotas are exhausted.
    """
    total_arrears = metrics.get("total_arrears", 0)
    par_pct = metrics.get("par_percentage", 0)
    accounts = metrics.get("accounts_in_arrears", 0)
    avg_days = metrics.get("average_days_past_due", 0)
    forecast = metrics.get("forecasting_30d", {})
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

    # 5. Forecast Fallback
    forecast_txt = "🔮 30-Day Outlook (Local)\n"
    if forecast:
        forecast_txt += f"- Predicted Exposure: KES {forecast.get('predicted_arrears_30d', 0):,.0f}\n"
        forecast_txt += f"- Trend: {forecast.get('trend', 'Stable')} | Momentum: {forecast.get('momentum', 'Neutral')}\n"

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
        "branch": branch_insights.strip(),
        "forecast": forecast_txt.strip()
    }

def _execute_agent_call(data: dict, system_prompt: str) -> str:
    """
    Unified production runner for all AI agents with model fallback and exponential backoff.
    """
    metrics_json = format_metrics(data)
    # Combine system persona and data context for the unified Gemini client
    full_prompt = f"{system_prompt}\n\nDATA TO ANALYZE:\n{metrics_json}"
    return generate_gemini_response(full_prompt)

def run_multi_agent_analysis(data: dict[str, Any]) -> dict[str, str]:
    """
    Orchestrates specialized interpreters.
    """
    return {
        "executive_summary": _execute_agent_call(data, RISK_ANALYST_SYSTEM_PROMPT),
        "risk": _execute_agent_call(data, RISK_ANALYSIS_AGENT_PROMPT),
        "recovery": _execute_agent_call(data, RECOVERY_STRATEGY_AGENT_PROMPT),
        "branch": _execute_agent_call(data, BRANCH_PERFORMANCE_ANALYST_PROMPT),
        "forecast": _execute_agent_call(data, FORECAST_AGENT_PROMPT)
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

    # Handle common non-serializable types recursively
    if obj is None or isinstance(obj, (str, bool)):
        return obj
        
    # Handle numeric types (Numpy and Python)
    if hasattr(obj, 'dtype'): # Numpy types
        if 'int' in str(obj.dtype): return int(obj)
        if 'float' in str(obj.dtype):
            val = float(obj)
            return 0.0 if (pd.isna(val) or np.isinf(val)) else round(val, 2)

    if isinstance(obj, (int, float)):
        if pd.isna(obj) or (isinstance(obj, float) and np.isinf(obj)):
            return 0.0
        return obj if isinstance(obj, int) else round(float(obj), 2)

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
        api_key = st.secrets.get("GEMINI_API_KEY")
        key_is_valid = api_key is not None and "REPLACE_WITH" not in str(api_key)
        
        is_functional = HAS_GENAI and key_is_valid
        st.session_state.ai_health = {
            "status": "Online" if is_functional else "Offline",
            "is_local": not is_functional,
            "last_success": "N/A",
            "model": "Gemini 2.5 Flash (Production)" if is_functional else "Deterministic Engine",
            "error": "" if is_functional else ("Library missing" if not HAS_GENAI else "Invalid/Placeholder API Key")
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
        if not HAS_GENAI or not st.secrets.get("GEMINI_API_KEY"):
            return generate_local_insights(metrics)

        # Attempt multi-agent AI analysis
        results = run_multi_agent_analysis(metrics)

        # Append the Gemini footer to the executive summary
        footer = f"\n\n---\n📈 AI Analytics Engine · Gemini 2.5 Flash · Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if "executive_summary" in results and not results["executive_summary"].startswith(("⚠️", "🛡️")):
            results["executive_summary"] += footer
        
        # Detection: If any agent returns an error signature, trigger the fallback engine
        # to ensure the UI remains clean and consistent.
        if any(v.startswith(("⚠️", "🛡️")) for v in results.values()):
            return generate_local_insights(metrics)
            
        return results
        
    except Exception as e:
        print(f"CRITICAL: AI Pipeline Failure: {str(e)}")
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
    if not HAS_GENAI or not st.secrets.get("GEMINI_API_KEY"):
        return f"🚨 [LOCAL FALLBACK] Recovery Report for {data['branch']}: Week movement is {data['net_movement']:,.0f}. Immediate field action required."

    prompt = f"{RECOVERY_MANAGER_PROMPT}\n\nWEEKLY METRICS:\n{json.dumps(data, indent=2)}"
    return generate_gemini_response(prompt)