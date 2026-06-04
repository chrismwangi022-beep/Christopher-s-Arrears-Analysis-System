"""
Spread Capital Limited — Predictive Arrears Forecasting
Enhanced Analytics & Multi-Window Forecasting Engine
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, Any, List, Tuple

def forecast_arrears_30d(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Predicts arrears exposure for the next 30 days using a hybrid approach 
    of EWMA smoothing and linear regression.
    
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
            "volatility_score": 0.0,
            "ma_7d": 0.0,
            "ma_30d": 0.0,
            "momentum": "Neutral"
        }

    # 1. Prepare Time Series
    ts = df.copy()
    ts['Report_Date'] = pd.to_datetime(ts['Report_Date'])
    daily_ts = ts.groupby('Report_Date')['Arrears'].sum().sort_index()
    
    # Fill missing dates in the sequence to ensure linear continuity
    all_dates = pd.date_range(start=daily_ts.index.min(), end=daily_ts.index.max(), freq='D')
    daily_ts = daily_ts.reindex(all_dates, fill_value=0)
    
    # Feature Engineering: Moving Averages
    ma_7 = daily_ts.rolling(window=7, min_periods=1).mean()
    ma_14 = daily_ts.rolling(window=14, min_periods=1).mean()
    ma_30 = daily_ts.rolling(window=30, min_periods=1).mean()
    
    # Exponential Weighting (Alpha 0.3 favors recent 3-5 days significantly)
    ewma = daily_ts.ewm(alpha=0.3, adjust=False).mean()
    
    # We only care about the last 30-45 days to establish a "current" trend
    window_size = min(len(daily_ts), 45)
    # Use smoothed EWMA data for regression to reduce outlier impact
    y = ewma.tail(window_size).values
    
    if len(y) < 3:
        return {
            "predicted_arrears_30d": float(daily_ts.iloc[-1]) if not daily_ts.empty else 0.0,
            "trend": "Insufficient Data",
            "confidence_score": 0.0,
            "volatility_score": 0.0,
            "ma_7d": float(ma_7.iloc[-1]),
            "ma_30d": float(ma_30.iloc[-1]),
            "momentum": "Neutral"
        }

    # 2. Linear Regression (y = mx + b)
    x = np.arange(len(y))
    
    # Fit line: slope (m) and intercept (b)
    try:
        m, b = np.polyfit(x, y, 1)
    except np.RankWarning:
        m, b = 0.0, y[-1]
    
    # Calculate R-Squared for confidence
    reconstructed_y = m * x + b
    residuals = y - reconstructed_y
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    # Volatility Score (Stability Indicator)
    # Higher residuals relative to mean = Higher instability
    mean_val = np.mean(y) if np.mean(y) != 0 else 1
    volatility = (np.std(residuals) / mean_val)

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
        
    # 5. Momentum Detection (Acceleration)
    # Compare 7-day velocity to overall 30-day velocity
    short_m = (y[-1] - y[-7]) / 7 if len(y) >= 7 else m
    momentum = "Accelerating ⚡" if short_m > m * 1.2 else "Decelerating 📉" if short_m < m * 0.8 else "Steady"

    # 6. Rolling Growth Rates
    growth_7d = (daily_ts.iloc[-1] - daily_ts.iloc[-7]) if len(daily_ts) >= 7 else 0

    return {
        "current_arrears": float(current_val),
        "predicted_arrears_30d": float(predicted_val),
        "expected_change": float(predicted_val - current_val),
        "trend": trend,
        "momentum": momentum,
        "confidence_score": round(float(max(0, min(1, r_squared))), 2),
        "volatility_score": round(float(volatility), 3),
        "ma_7d": float(ma_7.iloc[-1]),
        "ma_30d": float(ma_30.iloc[-1]),
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