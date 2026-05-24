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

def build_prompt(branch_name: str, current_week_data: pd.DataFrame, previous_week_data: pd.DataFrame) -> str:
    """
    Generates a structured prompt for Gemini AI following the Recovery Manager persona.
    Optimized for Gemini 2.5 Flash.
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

    # 👤 Loan Officer Performance Calculation
    all_dates = daily_stats.index.sort_values()
    start_dt, end_dt = all_dates[0], all_dates[-1]
    
    off_metrics = []
    for off in current_week_data['Loan_Officer'].unique():
        off_df = current_week_data[current_week_data['Loan_Officer'] == off]
        start_row = off_df[off_df['Report_Date'] == start_dt]
        end_row = off_df[off_df['Report_Date'] == end_dt]
        
        c_arr = end_row['Arrears'].sum() if not end_row.empty else 0
        o_arr = start_row['Arrears'].sum() if not start_row.empty else 0
        off_net = c_arr - o_arr
        off_dpd = end_row['Average_Days_Past_Due'].iloc[0] if not end_row.empty else 0
        
        status = "🟢 Performing Well"
        if off_net > 0 or off_dpd > 60: status = "🔴 High Risk Performance"
        elif off_net == 0 and c_arr > 0: status = "🟠 Needs Attention"
            
        off_metrics.append({"name": off, "arr": c_arr, "net": off_net, "dpd": off_dpd, "status": status})

    off_metrics.sort(key=lambda x: x['net'], reverse=True)
    best_officer = min(off_metrics, key=lambda x: x['net'])['name'] if off_metrics else "N/A"
    worst_officer = max(off_metrics, key=lambda x: x['net'])['name'] if off_metrics else "N/A"

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
ACT AS: A strict, aggressive, and no-nonsense Recovery Manager for Spread Capital.
TONE: Aggressive, blunt, and plain English ONLY. No corporate jargon. No soft language.

INSTRUCTIONS:
Generate a FULL detailed report as a collections command system. 
Do NOT summarize. Do NOT stop early. Complete ALL sections fully.

METRICS FOR BRANCH: {branch_name.upper()}
Opening: KSh {opening_arrears:,.0f} | Closing: KSh {closing_arrears:,.0f} | Net: KSh {net_movement:,.0f}
Peak: KSh {peak_arrears:,.0f} on {peak_date} | Spike: KSh {biggest_spike:,.0f} | Recovery: KSh {biggest_recovery:,.0f}
Volatility: {volatility_level} | Momentum: {recovery_momentum} | Pressure: {pressure_index}

OFFICER PERFORMANCE SUMMARY:
{chr(10).join([f"- {m['name']}: Arrears KSh {m['arr']:,.0f} | Net KSh {m['net']:,.0f} | Avg DPD: {m['dpd']:.1f} | {m['status']}" for m in off_metrics])}
Best Performer: {best_officer} | Worst Performer: {worst_officer}

CONTEXT: {comparison_note}

TASK: Generate a structured performance ultimatum. 
1. Evaluate officers ONLY within their assigned branch portfolio. DO NOT suggest cross-branch assignments.
2. Use precise language: "High arrears concentration under officer portfolio" or "Low recovery rate compared to branch average".
3. Inject behavioral commentary and operational pressure (bonus risks).

STRUCTURE (STRICT ADHERENCE REQUIRED FOR ALL SECTIONS):

🚩 [{branch_name.upper()}] – WEEKLY RECOVERY PERFORMANCE ULTIMATUM

👤 LOAN OFFICER PERFORMANCE REVIEW
Analyze each officer listed above. Classify them (🟢/🟠/🔴) and provide specific recovery instructions for their portfolios. 
Focus on field visit priorities and escalation triggers.

💀 THE DAMAGE
📉 WHERE WE FAILED
🔥 RECOVERY MOMENTUM
⚠️ PRESSURE INDEX

🥊 BATTLE PLAN
Split into:
- BRANCH-LEVEL ACTIONS: High-level strategic moves.
- OFFICER-LEVEL ACTIONS: Specific account handling focus per officer group.

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

    # 1. Load historical snapshots to provide true weekly movement context
    snapshot_file = "historical_branch_snapshots.csv"
    if os.path.exists(snapshot_file):
        hist_df = pd.read_csv(snapshot_file)
        # Map summary columns back to names expected by filtering/summarization utilities
        hist_df = hist_df.rename(columns={'Date': 'Report_Date', 'Total_Arrears': 'Arrears'})
        branch_df = hist_df[hist_df['Branch'] == branch_name].copy()
    else:
        # Fallback to current dashboard view if no history found
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

    model_name = "gemini-2.5-flash"
    init_status = "Initializing"

    try:
        genai.configure(api_key=api_key)
        print(f"Using Gemini model: {model_name}")
        try:
            model = genai.GenerativeModel(model_name)
            init_status = "Successful"
        except Exception as init_err:
            init_status = f"Failed: {str(init_err)}"
            raise init_err

        # 5. Generation parameters
        gen_config = {
            "temperature": 0.7,
            "max_output_tokens": 2500,
        }

        # 6. Execute generation with one automatic retry if truncation detected
        response = model.generate_content(prompt, generation_config=gen_config, request_options={"timeout": 30})
        report_text = response.text.strip()

        # Safety check: Detect missing end-of-report sections
        required_markers = ["🥊 BATTLE PLAN", "⚠️ WEEK-END WARNING", "⚡ FINAL WORD"]
        is_incomplete = not all(marker in report_text for marker in required_markers)

        if is_incomplete:
            print(f"DEBUG: Truncation detected for {branch_name}. Retrying generation...")
            response = model.generate_content(
                "The previous output was cut off. Please generate the FULL report from start to finish. " + prompt, 
                generation_config=gen_config, 
                request_options={"timeout": 35}
            )
            report_text = response.text.strip()

        return report_text
        
    except Exception as e:
        # Return FULL error details temporarily for debugging
        return f"""
Gemini Error: {str(e)}

DEBUG OUTPUTS:
- Selected Model: {model_name}
- Initialization Status: {init_status}
- Branch Name: {branch_name}
- Current Week Rows Count: {len(curr_week)}
- Opening Arrears: KSh {opening_arrears:,.0f}
- Closing Arrears: KSh {closing_arrears:,.0f}
- Net Movement: KSh {net_movement:,.0f}
""".strip()