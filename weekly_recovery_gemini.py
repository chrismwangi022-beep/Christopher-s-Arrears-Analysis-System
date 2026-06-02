"""
Spread Capital Limited — Weekly Recovery Intelligence Engine
Standalone Gemini AI Agent
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from src.ai_config import AI_MODEL_NAME

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Fallback for Streamlit environment
import streamlit as st
from src.gemini_client import generate_gemini_response

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
        "library_installed": HAS_GENAI,
        "api_key_found": False,
        "model_accessible": False,
        "error": None
    }

    if not HAS_GENAI:
        report["error"] = "google-genai library not found. Run: pip install google-genai"
        return report

    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        report["api_key_found"] = True
        try:
            # LEGACY SDK REMOVED: Configuration and Model instantiation cleared.
            report["model_accessible"] = False
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
    # Initialize with defaults for low activity or no current week data
    opening = 0.0
    closing = 0.0
    net_movement = 0.0
    trend_class = "No significant arrears movement detected this week."
    mom_class = "No recovery momentum observed due to low activity."
    max_spike = 0.0
    spike_date = "N/A"
    spike_severity = "None"
    recovery = 0.0
    reversal = False
    peak_arrears = 0.0
    peak_date = "N/A"
    total_principal = 0.0
    par_percent = 0.0
    worst_officers = []
    best_officers = []
    key_concern = "No current week activity data available."
    low_activity_flag = True # Assume low activity until proven otherwise

    curr_week = get_current_week(df)
    prev_week = get_previous_week(df)
    
    daily_stats = curr_week.groupby('Report_Date')['Arrears'].sum().sort_index()

    # Validation Debugging Prints
    print(f"DEBUG: Weekly Activity Data for {branch_name}")
    print(curr_week.head())
    print(f"Shape: {curr_week.shape}")
    if not curr_week.empty:
        print(f"Range: {curr_week['Report_Date'].min()} to {curr_week['Report_Date'].max()}")

    if not daily_stats.empty: # Only proceed with calculations if there's current week data
        low_activity_flag = False # Activity detected
        opening = float(daily_stats.iloc[0])
        closing = float(daily_stats.iloc[-1])
        net_movement = closing - opening
        diffs = daily_stats.diff().fillna(0)
        peak_arrears = float(daily_stats.max())
        peak_date = daily_stats.idxmax().strftime('%Y-%m-%d')

        # Principle Identification for PAR calculation
        p_col = 'Total_Principal' if 'Total_Principal' in curr_week.columns else ('Principle' if 'Principle' in curr_week.columns else ('Principal' if 'Principal' in curr_week.columns else None))
        if p_col:
            total_principal = float(curr_week.groupby('Report_Date')[p_col].sum().iloc[-1])
            par_percent = (closing / total_principal * 100) if total_principal > 0 else 0.0

        # Component 1: Trend Detection Engine
        move_ratio = net_movement / opening if opening > 0 else 0
        if move_ratio <= -0.05: trend_class = "Improving"
        elif move_ratio >= 0.10: trend_class = "Critical"
        elif move_ratio > 0: trend_class = "Worsening"
        else: trend_class = "Stable"

        # Component 2: Spike Detection Engine
        if not diffs.empty:
            max_spike = float(diffs.max())
            spike_date = diffs.idxmax().strftime('%Y-%m-%d')
            spike_severity = "Critical" if max_spike > 0.08 * opening and opening > 0 else "High" if max_spike > 0.04 * opening and opening > 0 else "Normal"
        
        # Component 4: Recovery Momentum Engine
        if len(diffs) > 0:
            rec_days = (diffs < 0).sum()
            consistency = rec_days / len(diffs)
            if consistency >= 0.6: mom_class = "Strengthening"
            elif consistency <= 0.2: mom_class = "Critical"
            elif consistency <= 0.4: mom_class = "Weakening"
            else: mom_class = "Stable"
            
            # Detect reversals (Spike larger than preceding recovery)
            reversal = any((diffs.iloc[i-1] < 0 and diffs.iloc[i] > abs(diffs.iloc[i-1])) for i in range(1, len(diffs)))
            recovery = float(abs(diffs.min())) if diffs.min() < 0 else 0.0

        # Officer Calculation
        all_dates = daily_stats.index.sort_values()
        start_dt, end_dt = all_dates[0], all_dates[-1]
        avg_branch_arr = curr_week.groupby('Loan_Officer')['Arrears'].sum().mean() if not curr_week.empty else 0
        
        off_metrics = []
        for off in curr_week['Loan_Officer'].unique():
            off_df = curr_week[curr_week['Loan_Officer'] == off]
            c_arr = off_df[off_df['Report_Date'] == end_dt]['Arrears'].sum() if end_dt in off_df['Report_Date'].values else 0
            o_arr = off_df[off_df['Report_Date'] == start_dt]['Arrears'].sum() if start_dt in off_df['Report_Date'].values else 0
            net = c_arr - o_arr
            dpd = off_df[off_df['Report_Date'] == end_dt]['Average_Days_Past_Due'].mean() if 'Average_Days_Past_Due' in off_df.columns and end_dt in off_df['Report_Date'].values else 0
            
            # Component 3: Officer Risk Engine
            status = "🟢 Improving" if net < 0 else "🟠 Needs attention"
            if net > 0 and dpd > 60: status = "🔴 Overloaded high-risk"
            elif dpd > 90 or (avg_branch_arr > 0 and c_arr > avg_branch_arr * 1.5): status = "🔴 Critical Watchlist"
            
            off_metrics.append({
                "name": off, 
                "arr": c_arr, 
                "net": net, 
                "dpd": dpd, 
                "status": status, 
                "rec": abs(net) if net < 0 else 0
            })

        off_metrics.sort(key=lambda x: x['net'], reverse=True)
        worst_officers = off_metrics[:3]
        remaining = [m for m in off_metrics if m not in worst_officers]
        best_officers = sorted(remaining, key=lambda x: x['net'])[:2]

        # Key Concern Logic
        if not prev_week.empty:
            prev_avg = prev_week['Arrears'].mean()
            curr_avg = curr_week['Arrears'].mean()
            if curr_avg > prev_avg:
                key_concern = f"Higher unpaid balances than last week (KSh {curr_avg - prev_avg:,.0f} avg increase)."
            else:
                key_concern = "Weekly performance shows improvement vs previous period."
        else:
            key_concern = "Previous week's data not available for comparison."

    return {
        "branch": branch_name.upper(),
        "opening": opening,
        "closing": closing,
        "movement": net_movement,
        "trend_class": trend_class,
        "mom_class": mom_class,
        "total_principal": total_principal,
        "par_percent": par_percent,
        "reversal": reversal,
        "peak_arrears": peak_arrears,
        "peak_date": peak_date,
        "spike_info": {"amount": max_spike, "date": spike_date, "severity": spike_severity},
        "recovery": recovery,
        "worst_officers": worst_officers,
        "best_officers": best_officers,
        "key_concern": key_concern,
        "low_activity_flag": low_activity_flag # Indicate if current week had no activity
    }

def generate_weekly_narrative(summary: dict) -> str:
    """
    STAGE 2 — NARRATIVE ENGINE
    Uses Gemini AI to generate a professional WhatsApp-ready report from computed summary.
    No calculations performed here.
    """
    # Prepare officer metrics for analysis
    all_officers = summary['worst_officers'] + summary['best_officers']
    officer_data_prompt = ""
    for m in all_officers:
        officer_data_prompt += f"Officer: {m['name']} | Arrears: KSh {m['arr']:,.0f} | Recovery: KSh {m['rec']:,.0f} | DPD: {m['dpd']:.1f} | Status: {m['status']}\n"

    prompt = f"""
You are a Credit Risk Reporting Engine for a regulated microfinance institution.

STRICT OUTPUT RULE:
You MUST follow the structure exactly.
Do NOT add extra text.
Do NOT omit fields.
Do NOT cut off officer comments.
Do NOT generate narrative outside defined sections.
If data is missing, write "N/A".

DATA FOR ANALYSIS:
Branch: {summary['branch']}
Closing Arrears: KSh {summary['closing']:,.0f}
Net Movement: KSh {summary['movement']:,.0f}
Trend: {summary['trend_class']}
Momentum: {summary['mom_class']}
Peak Arrears: KSh {summary['peak_arrears']:,.0f} on {summary['peak_date']}
Latest Spike: KSh {summary['spike_info']['amount']:,.0f} on {summary['spike_info']['date']}
Key Concern: {summary['key_concern']}
PAR Status: {summary.get('par_percent', 0):.2f}%
Recovery Status: {'Reversal detected' if summary['reversal'] else 'No significant post-collection slippage'}

OFFICER LIST:
{officer_data_prompt}

========================
📋 OUTPUT TEMPLATE (MUST FOLLOW EXACTLY)
========================

📋 BRANCH REPORT
Branch: {summary['branch']}
Current Unpaid Balances: KSh {summary['closing']:,.0f}
Change: KSh {summary['movement']:,.0f}
Overall Trend: {summary['trend_class']}

🔥 RECOVERY MOMENTUM
Momentum: {summary['mom_class']}
Recovery Status: {'Improving' if summary['movement'] < 0 else 'Deteriorating'}

⚠️ RISK LEVEL
Risk: {summary.get('par_percent', 0):.2f}% PAR
Risk Explanation: {summary['key_concern']}

💀 DAMAGE SUMMARY
Peak Balance: KSh {summary['peak_arrears']:,.0f} on {summary['peak_date']}
Latest Increase: KSh {summary['spike_info']['amount']:,.0f} on {summary['spike_info']['date']}

📉 PERFORMANCE NOTE
{summary['key_concern']}

👤 OFFICER SUMMARY
For EACH officer, output EXACTLY in this format:

Name: [Name]
Arrears: KSh [Arrears]
Recovery: KSh [Recovery]
DPD: [DPD]
Status: [Status]
Comment: [Generate a professional comment based on their metrics. Do not truncate.]

📡 BRANCH RECOVERY RADAR

High Priority Alerts:
- [Alert based on spikes or critical trends]

Officer Watchlist:
- [Officer names needing attention]

Operational Concerns:
- [Concerns about reversals or low recovery]

Positive Signals:
- [Signals from top performing officers]

========================
⚡ FINAL RULES
========================
- No emojis outside section headers
- No storytelling language
- No paragraphs
- No missing fields
- No duplicated sections
- No partial officer entries allowed
- Output must be complete and consistent
"""
    return generate_gemini_response(prompt)

def parse_radar_intelligence(report_text: str) -> dict:
    """
    Parses the raw text report to extract the Radar section into a structured dictionary.
    Useful for UI rendering of specific alerts and signals.
    """
    radar_data = {
        "alerts": [],
        "watchlist": [],
        "concerns": [],
        "signals": []
    }
    
    if not report_text or "📡 BRANCH RECOVERY RADAR" not in report_text:
        return radar_data
        
    try:
        radar_section = report_text.split("📡 BRANCH RECOVERY RADAR")[-1]
        for terminator in ["⚡ FINAL MESSAGE", "⚡ Final Message"]:
            if terminator in radar_section:
                radar_section = radar_section.split(terminator)[0]
        
        lines = radar_section.strip().split('\n')
        current_key = None
        
        mapping = {
            "High Priority Alerts": "alerts",
            "Officer Watchlist": "watchlist",
            "Operational Concerns": "concerns",
            "Positive Signals": "signals"
        }
        
        for line in lines:
            clean_line = line.strip().replace('*', '').replace('_', '')
            if not clean_line: continue
            
            header_found = False
            for header, key in mapping.items():
                if header in clean_line:
                    current_key = key
                    header_found = True
                    break
            
            if not header_found and current_key and (line.strip().startswith('-') or line.strip().startswith('*')):
                content = line.strip().lstrip('-*').strip()
                if content:
                    radar_data[current_key].append(content)
    except Exception:
        pass
            
    return radar_data

def generate_weekly_report(branch_name: str, df: pd.DataFrame, return_structured: bool = False) -> str | dict:
    """
    Orchestrates the two-stage AI reporting system.
    1. STAGE 1 — SUMMARY ENGINE (Pandas)
    2. STAGE 2 — NARRATIVE ENGINE (Gemini)
    """
    summary = build_weekly_summary(branch_name, df)
    if return_structured:
        return summary
    return generate_weekly_narrative(summary)