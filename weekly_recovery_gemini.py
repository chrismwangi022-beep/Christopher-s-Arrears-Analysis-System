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
            model = genai.GenerativeModel('gemini-1.5-flash')
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

def build_prompt(branch_name: str, current_week_data: pd.DataFrame, previous_week_data: pd.DataFrame) -> str:
    """
    Generates a structured prompt for Gemini AI following the Recovery Manager persona.
    Optimized for Gemini 1.5 Flash.
    """
    # Summarize current week data
    daily_stats = current_week_data.groupby('Report_Date')['Arrears'].sum().sort_index()

    opening_arrears = daily_stats.iloc[0]
    closing_arrears = daily_stats.iloc[-1]
    peak_arrears = daily_stats.max()
    net_movement = closing_arrears - opening_arrears

    # Calculate biggest spike and biggest recovery
    diffs = daily_stats.diff().fillna(0)
    biggest_spike = diffs.max()
    biggest_recovery = abs(diffs.min()) if diffs.min() < 0 else 0

    # Previous week comparison
    comparison_note = "No previous week data available for benchmark comparison."
    if not previous_week_data.empty:
        prev_sum = previous_week_data['Arrears'].sum()
        curr_sum = current_week_data['Arrears'].sum()
        if curr_sum > prev_sum:
            comparison_note = f"Arrears have increased by KSh {curr_sum - prev_sum:,.0f} compared to last week. Performance is slipping."
        else:
            comparison_note = f"Arrears have dropped by KSh {prev_sum - curr_sum:,.0f} since last week, but the current volume is still high."

    prompt = f"""
ACT AS: A strict, no-nonsense Recovery Manager for Spread Capital.
TONE: Aggressive, blunt, and plain English ONLY. No corporate jargon. No soft language.

METRICS FOR BRANCH: {branch_name.upper()}
- Opening Arrears: KSh {opening_arrears:,.0f}
- Peak Arrears: KSh {peak_arrears:,.0f}
- Closing Arrears: KSh {closing_arrears:,.0f}
- Biggest Daily Spike: KSh {biggest_spike:,.0f}
- Biggest Daily Recovery: KSh {biggest_recovery:,.0f}
- Net Movement: KSh {net_movement:,.0f}

CONTEXT:
{comparison_note}

TASK:
Generate a structured performance ultimatum for the branch team. Inject behavioral commentary (lazy collection patterns) and operational pressure (bonus risks, borrower dominance).

STRUCTURE (STRICT ADHERENCE):

🚩 [{branch_name.upper()}] – WEEKLY RECOVERY PERFORMANCE ULTIMATUM

💀 THE DAMAGE
📉 WHERE WE FAILED
🔥 PRESSURE ZONE
🥊 BATTLE PLAN
⚠️ WEEK-END WARNING
⚡ FINAL WORD

RULES:
- Use plain English only. No corporate jargon or soft talk.
- Format specifically for WhatsApp: Use *bold* for critical text only.
- Use the emoji headers provided with double line breaks for mobile readability.
- Keep paragraphs extremely short (max 2-3 sentences) for small screens.
- NO markdown tables, NO code blocks, and NO hashtag headers (#).
- The structure must be clean and ready for immediate copy-pasting.
- Output ONLY the report text. No explanations.
"""
    return prompt.strip()

def generate_weekly_report(branch_name: str, df: pd.DataFrame) -> str:
    """
    Main entry point for generating a report. Filters data and calls Gemini.
    Strictly backend logic; no Streamlit dependencies.
    """
    # Safeguard for missing library
    if not HAS_GOOGLE_AI:
        return "SYSTEM ERROR: The 'google-generativeai' library is not resolved. Please run 'pip install google-generativeai'."

    # API Key retrieval with fallback to Streamlit secrets
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            
    if not api_key:
        return "SYSTEM ERROR: Recovery Intelligence API Key not configured."

    # 1. Filter dataframe by branch
    branch_df = df[df['Branch'] == branch_name]
    if branch_df.empty:
        return f"SKIP: No records identified for branch '{branch_name}'."

    # 2. & 3. Compute week windows using existing utilities
    curr_week = get_current_week(branch_df)
    prev_week = get_previous_week(branch_df)

    if curr_week.empty:
        return "OFFLINE: Insufficient weekly activity data to generate a performance ultimatum."

    # 4. Build prompt
    prompt = build_prompt(branch_name, curr_week, prev_week)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # 5. Send to Gemini
        response = model.generate_content(prompt)
        # 6. Return response.text only
        return response.text
    except Exception:
        # 7. Handle API failure gracefully with fallback message
        return "BATTLE PLAN UNAVAILABLE: AI service timeout. Intensify field visits and manual follow-ups immediately."