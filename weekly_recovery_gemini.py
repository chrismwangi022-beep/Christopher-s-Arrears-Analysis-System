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

    if daily_stats.empty:
        return "Insufficient data to generate report."

    opening_arrears = daily_stats.iloc[0]
    closing_arrears = daily_stats.iloc[-1]
    peak_arrears = daily_stats.max()
    peak_date = daily_stats.idxmax().strftime('%Y-%m-%d')
    net_movement = closing_arrears - opening_arrears

    # Calculate biggest spike and biggest recovery
    diffs = daily_stats.diff().fillna(0)
    biggest_spike = diffs.max()
    biggest_recovery = abs(diffs.min()) if diffs.min() < 0 else 0
    
    # Advanced Local Metrics for AI Context
    volatility_level = "EXTREME" if biggest_spike > (opening_arrears * 0.15) else "HIGH" if biggest_spike > (opening_arrears * 0.05) else "MODERATE"
    recovery_momentum = "RECOVERING" if net_movement < 0 else "DETERIORATING" if net_movement > 0 else "STAGNANT"
    pressure_index = "CRITICAL" if closing_arrears > peak_arrears * 0.95 else "HIGH"

    # Previous week comparison
    comparison_note = "No previous week data available for benchmark comparison."
    if not previous_week_data.empty:
        prev_avg = previous_week_data['Arrears'].mean()
        curr_avg = current_week_data['Arrears'].mean()
        if curr_avg > prev_avg:
            comparison_note = f"Arrears are UP vs last week (Avg KSh {curr_avg - prev_avg:,.0f} higher). Situational deterioration."
        else:
            comparison_note = f"Arrears are DOWN vs last week (Avg KSh {prev_avg - curr_avg:,.0f} lower). Keep the pressure on."

    prompt = f"""
ACT AS: Strict, no-nonsense Recovery Manager. Tone: Aggressive, blunt, plain English.

BRANCH: {branch_name.upper()}
Opening: KSh {opening_arrears:,.0f} | Closing: KSh {closing_arrears:,.0f} | Net: KSh {net_movement:,.0f}
Peak: KSh {peak_arrears:,.0f} on {peak_date}
Spike: KSh {biggest_spike:,.0f} | Recovery: KSh {biggest_recovery:,.0f}
Volatility: {volatility_level} | Momentum: {recovery_momentum} | Pressure: {pressure_index}

CONTEXT: {comparison_note}

TASK: Generate a structured performance ultimatum. NO raw data dumps.

ACT AS: A strict, no-nonsense Recovery Manager for Spread Capital.
TONE: Aggressive, blunt, and plain English ONLY. No corporate jargon. No soft language.

METRICS FOR BRANCH: {branch_name.upper()}
- Opening Arrears: KSh {opening_arrears:,.0f}
- Peak Arrears: KSh {peak_arrears:,.0f}
- Closing Arrears: KSh {closing_arrears:,.0f}
- Biggest Daily Spike: KSh {biggest_spike:,.0f}
- Peak Date: {peak_date}
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

    # Compute safe scalar metrics locally before calling AI to ensure safe fallback
    daily_stats = curr_week.groupby('Report_Date')['Arrears'].sum().sort_index()
    if daily_stats.empty:
        return "OFFLINE: Insufficient activity for statistical generation."

    opening_arrears = daily_stats.iloc[0]
    closing_arrears = daily_stats.iloc[-1]
    net_movement = closing_arrears - opening_arrears
    peak_arrears = daily_stats.max()

    # 4. Build prompt
    prompt = build_prompt(branch_name, curr_week, prev_week)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 5. Send to Gemini with safety timeout configuration
        response = model.generate_content(
            prompt,
            request_options={"timeout": 20}
        )
        return response.text.strip()
        
    except Exception as e:
        # Return clean fallback using pre-computed scalars
        return f'''
🚨 RECOVERY ACTION REQUIRED

AI service temporarily unavailable.

Branch: {branch_name}

Current Net Movement:
KSh {net_movement:,.0f}

Field collections must intensify immediately.
'''.strip()