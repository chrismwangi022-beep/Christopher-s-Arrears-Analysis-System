"""
Spread Capital Limited — Weekly Recovery Intelligence Engine
Standalone Gemini AI Agent
"""

import google.generativeai as genai
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def get_current_week(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters dataframe for the current operational week: 
    Start: latest Monday
    End: current date
    """
    if df.empty or 'Report_Date' not in df.columns:
        return pd.DataFrame()
    
    # Create working copy with robust datetime handling
    df_temp = df.copy()
    df_temp['Report_Date'] = pd.to_datetime(df_temp['Report_Date'], errors='coerce')
    df_temp = df_temp.dropna(subset=['Report_Date'])
    
    # Identify latest Monday relative to today using pandas Timestamp
    today_norm = pd.Timestamp.now().normalize()
    monday = today_norm - pd.Timedelta(days=today_norm.weekday())
    
    # Filter dataframe from Monday -> today
    return df_temp[(df_temp['Report_Date'] >= monday) & (df_temp['Report_Date'] <= pd.Timestamp.now())]

def get_previous_week(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns data before the current week for comparison context in AI prompt.
    """
    if df.empty or 'Report_Date' not in df.columns:
        return pd.DataFrame()

    df_temp = df.copy()
    df_temp['Report_Date'] = pd.to_datetime(df_temp['Report_Date'], errors='coerce')
    df_temp = df_temp.dropna(subset=['Report_Date'])

    today_norm = pd.Timestamp.now().normalize()
    current_monday = today_norm - pd.Timedelta(days=today_norm.weekday())
    
    prev_monday = current_monday - pd.Timedelta(days=7)
    prev_sunday = current_monday - pd.Timedelta(seconds=1)

    return df_temp[(df_temp['Report_Date'] >= prev_monday) & (df_temp['Report_Date'] <= prev_sunday)]

def build_prompt(branch_name: str, current_week_data: pd.DataFrame, previous_week_data: pd.DataFrame) -> str:
    """
    Constructs the aggressive, strict Recovery Manager prompt for Gemini.
    """
    # Calculate core metrics for the prompt context
    daily_arrears = current_week_data.groupby('Report_Date')['Arrears'].sum().sort_index()
    
    opening = daily_arrears.iloc[0]
    closing = daily_arrears.iloc[-1]
    peak = daily_arrears.max()
    peak_date = daily_arrears.idxmax().strftime('%b %d')
    net_movement = closing - opening
    
    diffs = daily_arrears.diff().fillna(0)
    max_spike = diffs.max()
    max_recovery = abs(diffs.min()) if diffs.min() < 0 else 0
    
    prev_context = "No historical deterioration context available."
    if not previous_week_data.empty:
        prev_sum = previous_week_data.groupby('Report_Date')['Arrears'].sum()
        prev_avg = prev_sum.mean()
        prev_context = f"PREVIOUS WEEK AVG ARREARS: KSh {prev_avg:,.0f}"

    prompt = f"""
ACT AS: A strict, aggressive, and frustrated Recovery Manager. 
TONE: Blunt, operational, and field-focused. NO corporate jargon. NO synergies. NO soft language.
GOAL: Generate a WhatsApp-ready recovery performance ultimatum for {branch_name}.

METRICS FOR {branch_name.upper()}:
- Period: Monday to Today
- Opening Arrears: KSh {opening:,.0f}
- Peak Arrears: KSh {peak:,.0f} on {peak_date}
- Closing Arrears: KSh {closing:,.0f}
- Net Movement: KSh {net_movement:,.0f}
- Highest Single-Day Deterioration: KSh {max_spike:,.0f}
- Strongest Recovery Day: KSh {max_recovery:,.0f}
- {prev_context}

OUTPUT STRUCTURE (STRICT ADHERENCE REQUIRED):
🚩 [BRANCH NAME] – WEEKLY RECOVERY PERFORMANCE ULTIMATUM
Period: Monday - {datetime.now().strftime('%b %d, %Y')}

🔥 RECOVERY MOMENTUM
[IMPROVING / STAGNANT / WEAKENING / CRITICAL]

⚠️ PRESSURE INDEX
[LOW / MODERATE / HIGH / EXTREME]

📍 BRANCH STATUS
[Stable / Recovering / Unstable / Deteriorating / Critical]

💀 THE DAMAGE (The Numbers)
Summarize opening, peak (with date), closing, movement, spike, and recovery day. Use KSh.

📉 WHERE WE FAILED
[2–4 aggressive operational paragraphs. Call out lazy collection patterns and weak follow-through based on the movement numbers provided.]

🔥 THE PRESSURE ZONE
[Explain operational danger: bonus pressure, borrower dominance, risk escalation.]

🥊 BATTLE PLAN: NO EXCUSES
Immediate Target: [Dynamic KSh amount]
Field Intensity: [NORMAL / HIGH / EXTREME]
Field Strategy: [Demand face-to-face collections]
The "Red Line": [Dynamic KSh threshold branch must not cross]

⚠️ WEEK-END WARNING
[Operational warning based on data trends.]

⚡ FINAL WORD
[Very aggressive closing statement.]

RULES:
- WhatsApp-ready formatting (proper spacing for mobile).
- NO markdown tables.
- Return ONLY the final report text.
"""
    return prompt

def generate_weekly_report(branch_name: str, df: pd.DataFrame) -> str:
    """
    Main entry point for generating a report. Filters data and calls Gemini.
    """
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "ERROR: Gemini API Key missing from secrets."

    genai.configure(api_key=api_key)
    # Using requested model string
    model = genai.GenerativeModel('gemini-2.0-flash')

    branch_df = df[df['Branch'] == branch_name].copy()
    if branch_df.empty: return f"ERROR: Branch '{branch_name}' not found."

    # Week Logic
    curr_week = get_current_week(branch_df)
    if curr_week.empty: return "ERROR: Insufficient data for the current week window."

    # Historical Context (Previous Week)
    prev_week = get_previous_week(branch_df)

    prompt = build_prompt(branch_name, curr_week, prev_week)

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"ERROR: Gemini failed to generate report. {str(e)}"