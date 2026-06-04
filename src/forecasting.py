"""
Spread Capital Limited — Predictive Arrears Forecasting
Lightweight Trend-Based Regression Engine
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, Any, List

def forecast_arrears_30d(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Predicts arrears exposure for the next 30 days using linear regression.
    
    Args:
        df: Dataframe with 'Report_Date' and 'Arrears'
        
    Returns:
        Dictionary containing forecast, trend, and confidence metrics.
    """
    if df.empty or 'Report_Date' not in df.columns or 'Arrears' not in df.columns:
        return {
            "predicted_arrears_30d": 0.0,
            "trend": "Stable",
            "confidence_score": 0.0,
            "growth_rate": 0.0
        }

    # 1. Prepare Time Series
    ts = df.copy()
    ts['Report_Date'] = pd.to_datetime(ts['Report_Date'])
    daily_ts = ts.groupby('Report_Date')['Arrears'].sum().sort_index()
    
    # Fill missing dates in the sequence to ensure linear continuity
    all_dates = pd.date_range(start=daily_ts.index.min(), end=daily_ts.index.max(), freq='D')
    daily_ts = daily_ts.reindex(all_dates, fill_value=0)
    
    # We only care about the last 30-45 days to establish a "current" trend
    window_size = min(len(daily_ts), 45)
    recent_data = daily_ts.tail(window_size)
    
    if len(recent_data) < 3:
        return {
            "predicted_arrears_30d": float(daily_ts.iloc[-1]) if not daily_ts.empty else 0.0,
            "trend": "Insufficient Data",
            "confidence_score": 0.0,
            "growth_rate": 0.0
        }

    # 2. Linear Regression (y = mx + b)
    y = recent_data.values
    x = np.arange(len(y))
    
    # Fit line: slope (m) and intercept (b)
    m, b = np.polyfit(x, y, 1)
    
    # Calculate R-Squared for confidence
    reconstructed_y = m * x + b
    residuals = y - reconstructed_y
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    # 3. Project 30 Days Ahead
    # We project from the current day (index len(y)-1) to 30 days out
    current_val = y[-1]
    future_x = (len(y) - 1) + 30
    predicted_val = m * future_x + b
    
    # Ensure we don't predict negative arrears
    predicted_val = max(0, predicted_val)

    # 4. Determine Trend Direction
    # Use a 1% threshold for stability
    threshold = 0.01 * current_val if current_val > 0 else 100
    if m > (threshold / 30):
        trend = "Upward ↑"
    elif m < -(threshold / 30):
        trend = "Downward ↓"
    else:
        trend = "Stable →"

    # 5. Rolling Growth Rates (Check for acceleration)
    growth_7d = (daily_ts.iloc[-1] - daily_ts.iloc[-7]) if len(daily_ts) >= 7 else 0

    return {
        "current_arrears": float(current_val),
        "predicted_arrears_30d": float(predicted_val),
        "expected_change": float(predicted_val - current_val),
        "trend": trend,
        "confidence_score": round(max(0, min(1, r_squared)), 2),
        "daily_velocity": float(m),
        "growth_7d_total": float(growth_7d)
    }

def get_forecast_by_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Helper to run forecasts across different segments."""
    results = []
    for name, group in df.groupby(group_col):
        f = forecast_arrears_30d(group)
        f[group_col] = name
        results.append(f)
    return pd.DataFrame(results)