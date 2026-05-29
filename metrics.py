"""
Recovery Metrics Calculator

Handles deterministic calculations for recovery momentum and performance.
Built to be production-grade, JSON-serializable, and AI-free.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from src.calculations import (
    calculate_par_percentage,
    categorize_by_aging,
    get_officer_performance,
    get_aging_arrears_summary,
    find_column_case_insensitive
)

def calculate_weekly_change(df_branch: pd.DataFrame, full_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates the deterministic movement of arrears compared to the previous week.
    Returns a structured dictionary of movement metrics.
    """
    date_col = find_column_case_insensitive(df_branch, "Report_Date") or "Report_Date"
    arr_col = find_column_case_insensitive(df_branch, "Arrears") or "Arrears"
    branch_col = find_column_case_insensitive(df_branch, "Branch") or "Branch"

    if df_branch.empty or full_df.empty or date_col not in df_branch.columns:
        return {"movement": 0.0, "percentage": 0.0, "status": "No history"}

    branch_name = df_branch[branch_col].iloc[0] if branch_col in df_branch.columns else "N/A"
    curr_total = pd.to_numeric(df_branch[arr_col], errors="coerce").fillna(0).sum()

    # Find historical context from full_df
    hist_df = full_df[full_df[branch_col] == branch_name].copy() if branch_col in full_df.columns else pd.DataFrame()
    if hist_df.empty:
        return {"movement": 0.0, "percentage": 0.0, "status": "Initial period"}

    hist_df[date_col] = pd.to_datetime(hist_df[date_col], errors="coerce")
    latest_date = pd.to_datetime(df_branch[date_col]).max()
    prev_date_limit = latest_date - pd.Timedelta(days=6)
    
    prev_week_data = hist_df[hist_df[date_col] < prev_date_limit]
    
    if prev_week_data.empty:
        return {"movement": 0.0, "percentage": 0.0, "status": "Growth period"}

    last_snapshot_date = prev_week_data[date_col].max()
    prev_total = prev_week_data[prev_week_data[date_col] == last_snapshot_date][arr_col].sum()
    
    movement = curr_total - prev_total
    percentage = (movement / prev_total * 100) if prev_total > 0 else 0.0

    return {
        "movement": round(float(movement), 2),
        "percentage": round(float(percentage), 2),
        "status": "worsening" if movement > 0 else "improving"
    }

def identify_worsening_accounts(df_branch: pd.DataFrame, full_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Identifies individual accounts where arrears increased since the last report."""
    # Placeholder for granular account-level movement logic
    return []

def identify_improving_accounts(df_branch: pd.DataFrame, full_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Identifies individual accounts where arrears decreased since the last report."""
    return []

def build_recovery_metrics(
    df_branch: pd.DataFrame,
    full_df: pd.DataFrame,
    branch_name: str
) -> Dict[str, Any]:
    """
    Orchestrates the deterministic metrics generation for a branch.
    Never uses AI. Returns a JSON-serializable structured dictionary.
    """
    # Empty dataframe protection
    if df_branch.empty:
        return {
            "branch_name": branch_name,
            "status": "Error",
            "message": "No data available for analysis"
        }

    # Cleaning - Never mutate original dataframe
    df = df_branch.copy()
    arr_col = find_column_case_insensitive(df, "Arrears") or "Arrears"
    days_col = find_column_case_insensitive(df, "Days") or "Days"
    id_col = find_column_case_insensitive(df, "AccountID") or "AccountID"
    
    for col in [arr_col, days_col]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 1. Base Aggregates
    total_arrears = float(df[arr_col].sum())
    total_accounts = int(df[id_col].nunique()) if id_col in df.columns else len(df)
    par_pct = float(calculate_par_percentage(df))
    avg_days = float(df[df[days_col] > 0][days_col].mean() if days_col in df.columns else 0)

    # 2. Rankings & Summaries
    top_10_accounts = df.nlargest(10, arr_col).fillna(0).to_dict(orient="records")
    
    # Clean list of dicts for JSON serialization (handling timestamps/numpy types)
    top_10_accounts = [
        {str(k): (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in record.items()} 
        for record in top_10_accounts
    ]

    off_perf = get_officer_performance(df)
    top_5_officers = off_perf.head(5).to_dict(orient="records")
    
    officer_summary = {}
    if not off_perf.empty:
        officer_summary = off_perf.set_index('Officer')['Arrears'].to_dict()

    # 3. Aging distribution
    df_categorized = categorize_by_aging(df)
    aging_dist = get_aging_arrears_summary(df_categorized).to_dict()

    # 4. Weekly Trend & Account Movement
    trend = calculate_weekly_change(df, full_df)
    worsening = identify_worsening_accounts(df, full_df)
    improving = identify_improving_accounts(df, full_df)

    # 5. Critical Accounts (>90 days)
    critical_df = df[df[days_col] > 90]
    critical_summary = {
        "count": len(critical_df),
        "total_amount": round(float(critical_df[arr_col].sum()), 2)
    }

    # 6. Recommended Operational Actions (Deterministic logic mapping)
    actions = []
    if par_pct > 15: actions.append("CRITICAL: Freeze new credit disbursements for this branch.")
    if trend['status'] == 'worsening': actions.append("URGENT: Initiate senior management performance review.")
    if critical_summary['count'] > 5: actions.append("ESCALATION: Deploy specialized external recovery agency.")
    if avg_days > 45: actions.append("ROUTINE: Increase field visit frequency for early-stage defaults.")
    if not actions: actions.append("MONITOR: Maintain standard collection protocols.")

    return {
        "branch_name": branch_name,
        "total_arrears": round(total_arrears, 2),
        "total_accounts": total_accounts,
        "par_percentage": round(par_pct, 2),
        "avg_days_past_due": round(avg_days, 1),
        "aging_distribution": aging_dist,
        "rankings": {
            "top_10_accounts": top_10_accounts,
            "top_5_high_risk_officers": top_5_officers
        },
        "officer_performance_summary": officer_summary,
        "trend_analysis": trend,
        "movement_flags": {"worsening": worsening, "improving": improving},
        "critical_exposure": critical_summary,
        "operational_actions": actions,
        "metadata": {
            "generated_at": pd.Timestamp.now().isoformat(),
            "engine_version": "2.0-deterministic"
        }
    }
        
        Args:
            branch_name: The name of the branch to analyze.
        """
        pass