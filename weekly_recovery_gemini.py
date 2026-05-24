"""
Spread Capital Limited — Weekly Recovery Intelligence Engine
Standalone Gemini AI Agent
"""

import os
import pandas as pd
from datetime import datetime, timedelta

try:
    import google.generativeai as genai
    HAS_GOOGLE_AI = True
except ImportError:
    HAS_GOOGLE_AI = False

# Fallback for Streamlit environment
import streamlit as st

def update_historical_snapshots(df: pd.DataFrame):
    """
    Builds and updates a daily historical snapshot CSV for branch-level metrics.
    Ensures persistent tracking of arrears movement over time for AI analysis.
    """
    snapshot_file = "historical_branch_snapshots.csv"
    
    # Check for mandatory columns
    required = {'Branch', 'Arrears', 'Report_Date'}
    if df.empty or not required.issubset(df.columns):
        return

    # 1. Summarize input data by Date, Branch, and Loan Officer
    temp = df.copy()
    temp['Report_Date'] = pd.to_datetime(temp['Report_Date'], errors='coerce').dt.normalize()
    temp = temp.dropna(subset=['Report_Date'])
    
    if temp.empty:
        return

    # Identify principle column (handle spelling variation used in project)
    p_col = 'Principle' if 'Principle' in temp.columns else ('Principal' if 'Principal' in temp.columns else None)
    
    # Aggregation
    summary = temp.groupby(['Report_Date', 'Branch', 'Loan_Officer']).agg(
        Total_Arrears=('Arrears', 'sum'),
        Total_Principal=(p_col, 'sum') if p_col else ('Arrears', lambda x: 0),
        Average_Days_Past_Due=('Days', 'mean') if 'Days' in temp.columns else ('Arrears', lambda x: 0),
        Account_Count=('AccountID', 'count') if 'AccountID' in temp.columns else ('Arrears', 'count')
    ).reset_index()

    # Calculate Metrics
    summary['PAR'] = (summary['Total_Arrears'] / summary['Total_Principal']).fillna(0).replace([float('inf'), -float('inf')], 0)
    summary['Date'] = summary['Report_Date'].dt.strftime('%Y-%m-%d')
    
    # Structure per requirements
    summary = summary[['Date', 'Branch', 'Loan_Officer', 'Total_Arrears', 'Total_Principal', 'PAR', 'Average_Days_Past_Due', 'Account_Count']]

    # 2. Persist to CSV (Append or Update)
    if os.path.exists(snapshot_file):
        try:
            hist_df = pd.read_csv(snapshot_file)
            hist_df['Date'] = hist_df['Date'].astype(str)
            summary['Date'] = summary['Date'].astype(str)
            
            # Combine and remove duplicates (latest data for a date/branch combo wins)
            combined = pd.concat([hist_df, summary]).drop_duplicates(subset=['Date', 'Branch', 'Loan_Officer'], keep='last')
            combined.to_csv(snapshot_file, index=False)
        except Exception:
            summary.to_csv(snapshot_file, index=False)
    else:
        summary.to_csv(snapshot_file, index=False)

def verify_gemini_setup() -> dict:
    """
    Diagnostic utility to verify Gemini AI environment configuration.
    Returns a status report for connectivity and model accessibility.
    """
    report = {
        "library_installed": HAS_GOOGLE_AI,
        "api_key_found": False,
        "model_accessible": False,
        "error": None
    }

    if not HAS_GOOGLE_AI:
        report["error"] = "google-generativeai library not found. Run: pip install google-generativeai"
        return report

    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        report["api_key_found"] = True
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            # Lightweight check for model initialization
            report["model_accessible"] = True
        except Exception as e:
            report["error"] = str(e)
    
    return report

def get_current_week(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters dataframe for the current operational week: 
    - Start: Latest Monday relative to today
    - End: Current timestamp
    """
    if df.empty or 'Report_Date' not in df.columns:
        return pd.DataFrame()
    
    df_temp = df.copy()
    # Coerce to datetime and force to naive to avoid timezone comparison issues
    df_temp['Report_Date'] = pd.to_datetime(df_temp['Report_Date'], errors='coerce').dt.tz_localize(None)
    df_temp = df_temp.dropna(subset=['Report_Date'])
    
    # Determine Monday of the current week
    now = pd.Timestamp.now().tz_localize(None)
    today = now.normalize()
    monday = today - pd.Timedelta(days=today.weekday())
    
    return df_temp[(df_temp['Report_Date'] >= monday) & (df_temp['Report_Date'] <= now)]

def get_previous_week(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns data for the 7-day window preceding the current Monday.
    Used for historical performance context in AI analysis.
    """
    if df.empty or 'Report_Date' not in df.columns:
        return pd.DataFrame()

    df_temp = df.copy()
    # Coerce to datetime and force to naive to avoid timezone comparison issues
    df_temp['Report_Date'] = pd.to_datetime(df_temp['Report_Date'], errors='coerce').dt.tz_localize(None)
    df_temp = df_temp.dropna(subset=['Report_Date'])

    today = pd.Timestamp.now().tz_localize(None).normalize()
    current_monday = today - pd.Timedelta(days=today.weekday())
    
    prev_monday = current_monday - pd.Timedelta(days=7)
    prev_period_end = current_monday - pd.Timedelta(seconds=1)

    return df_temp[(df_temp['Report_Date'] >= prev_monday) & (df_temp['Report_Date'] <= prev_period_end)]

def build_weekly_summary(branch_name: str, df: pd.DataFrame) -> dict:
    """
    STAGE 1 — SUMMARY ENGINE
    Computes branch-level metrics and officer performance using pandas only.
    No Gemini calls or narrative writing.
    """
    curr_week = get_current_week(df)
    prev_week = get_previous_week(df)
    
    daily_stats = curr_week.groupby('Report_Date')['Arrears'].sum().sort_index()
    if daily_stats.empty:
        return {}

    opening = daily_stats.iloc[0]
    closing = daily_stats.iloc[-1]
    net_movement = closing - opening
    diffs = daily_stats.diff().fillna(0)
    
    # Trend & Risk Logic
    trend = "Improving" if net_movement < 0 else "Worsening" if net_movement > 0 else "Stable"
    risk_level = "Critical" if closing > daily_stats.max() * 0.95 else "High" if net_movement > 0 else "Controlled"
    recovery_status = "Good recovery momentum" if net_movement < 0 else "Slow recovery activity"

    # Officer Calculation
    all_dates = daily_stats.index.sort_values()
    start_dt, end_dt = all_dates[0], all_dates[-1]
    off_metrics = []
    for off in curr_week['Loan_Officer'].unique():
        off_df = curr_week[curr_week['Loan_Officer'] == off]
        c_arr = off_df[off_df['Report_Date'] == end_dt]['Arrears'].sum()
        o_arr = off_df[off_df['Report_Date'] == start_dt]['Arrears'].sum()
        net = c_arr - o_arr
        dpd = off_df[off_df['Report_Date'] == end_dt]['Average_Days_Past_Due'].mean() if 'Average_Days_Past_Due' in off_df.columns else 0
        
        status = "🟢 Doing well"
        if net > 0 or dpd > 60: status = "🔴 Requires close follow-up"
        elif net == 0 and c_arr > 0: status = "🟠 Needs attention"
        
        off_metrics.append({
            "name": off, 
            "arr": c_arr, 
            "net": net, 
            "dpd": dpd, 
            "status": status, 
            "rec": abs(net) if net < 0 else 0
        })

    off_metrics.sort(key=lambda x: x['net'], reverse=True)
    worst_3 = off_metrics[:3]
    remaining = [m for m in off_metrics if m not in worst_3]
    best_2 = sorted(remaining, key=lambda x: x['net'])[:2]

    # Key Concern Logic
    key_concern = "Unpaid balances are stable."
    if not prev_week.empty:
        prev_avg = prev_week['Arrears'].mean()
        curr_avg = curr_week['Arrears'].mean()
        if curr_avg > prev_avg:
            key_concern = f"Higher unpaid balances than last week (KSh {curr_avg - prev_avg:,.0f} avg increase)."
        else:
            key_concern = "Weekly performance shows improvement vs previous period."

    return {
        "branch": branch_name.upper(),
        "opening": opening,
        "closing": closing,
        "movement": net_movement,
        "trend": trend,
        "risk_level": risk_level,
        "peak_arrears": daily_stats.max(),
        "peak_date": daily_stats.idxmax().strftime('%Y-%m-%d'),
        "spike": diffs.max(),
        "recovery": abs(diffs.min()) if diffs.min() < 0 else 0,
        "worst_officers": worst_3,
        "best_officers": best_2,
        "key_concern": key_concern,
        "recovery_status": recovery_status
    }

def generate_weekly_narrative(summary: dict) -> str:
    """
    STAGE 2 — NARRATIVE ENGINE
    Uses Gemini AI to generate a professional WhatsApp-ready report from computed summary.
    No calculations performed here.
    """
    if not summary:
        return "OFFLINE: Insufficient activity data to generate report."

    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "SYSTEM ERROR: Gemini API Key not configured."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Compact officer text for prompt
        worst_txt = "\n".join([f"- {m['name']}: KSh {m['arr']:,.0f} Arrears | {m['rec']:,.0f} Recovery | {m['dpd']:.1f} DPD | {m['status']}" for m in summary['worst_officers']])
        best_txt = "\n".join([f"- {m['name']}: KSh {m['arr']:,.0f} Arrears | {m['rec']:,.0f} Recovery | {m['dpd']:.1f} DPD | {m['status']}" for m in summary['best_officers']])

        prompt = f"""
ACT AS: A Professional Portfolio Manager for Spread Capital.
TONE: Professional, respectful, firm, and simple English.

DATA SUMMARY:
Branch: {summary['branch']}
Arrears: Opening KSh {summary['opening']:,.0f} -> Closing KSh {summary['closing']:,.0f} (Net: KSh {summary['movement']:,.0f})
Trend: {summary['trend']} | Risk: {summary['risk_level']} | Status: {summary['recovery_status']}
Peak: KSh {summary['peak_arrears']:,.0f} on {summary['peak_date']}
Spike: KSh {summary['spike']:,.0f} | Max Recovery: KSh {summary['recovery']:,.0f}
Key Concern: {summary['key_concern']}

OFFICERS NEEDING ATTENTION:
{worst_txt}

TOP OFFICERS:
{best_txt}

TASK:
Generate a structured Weekly Recovery Performance Report for WhatsApp.
Use sections: 🚩 Branch Report, 🔥 Recovery Momentum, ⚠️ Risk Level, 💀 Damage, 📉 Improvement Needed, 👤 Officer Summary, 🥊 Action Plan, ⚡ Final Message.

RULES:
1. Simple English only (e.g., "High unpaid balances" instead of "concentration").
2. Officer section MUST use this format:
   [Name]
   Arrears: KSh [Amt] | Recovery: KSh [Amt] | DPD: [Val]
   Status: [Status]
   Comment: [One short sentence]
3. Ensure the report is fully completed. Do not stop mid-officer.
4. Formatting: *bold* for critical info, emoji headers, extremely short paragraphs.
5. Output ONLY the report text.
"""
        config = {
            "temperature": 0.4,
            "max_output_tokens": 2200
        }

        response = model.generate_content(prompt, generation_config=config, request_options={"timeout": 40})
        return response.text.strip()

    except Exception as e:
        return f"Gemini Narrative Error: {str(e)}"

def generate_weekly_report(branch_name: str, df: pd.DataFrame) -> str:
    """
    Orchestrates the two-stage AI reporting system.
    1. STAGE 1 — SUMMARY ENGINE (Pandas)
    2. STAGE 2 — NARRATIVE ENGINE (Gemini)
    """
    # 1. Load historical snapshots to provide true weekly movement context
    snapshot_file = "historical_branch_snapshots.csv"
    branch_df = pd.DataFrame()
    if os.path.exists(snapshot_file):
        hist_df = pd.read_csv(snapshot_file)
        hist_df = hist_df.rename(columns={'Date': 'Report_Date', 'Total_Arrears': 'Arrears'})
        branch_df = hist_df[hist_df['Branch'] == branch_name].copy()
    
    if branch_df.empty:
        branch_df = df[df['Branch'] == branch_name]

    if branch_df.empty:
        return f"SKIP: No records identified for branch '{branch_name}'."

    # Stage 1: Summary Engine
    summary = build_weekly_summary(branch_name, branch_df)
    
    # Stage 2: Narrative Engine
    return generate_weekly_narrative(summary)