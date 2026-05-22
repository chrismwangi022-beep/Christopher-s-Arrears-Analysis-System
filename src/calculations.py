"""
Spread Capital Limited — Strict Financial Calculation Engine
Source of Truth for Arrears Metrics & Risk Aggregations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from .constants import AGING_BUCKETS


def _safe_divide(numerator: float, denominator: float) -> float:
    """
    Base division logic for ratios (0.0 to 1.0+). 
    """
    if pd.isna(numerator) or pd.isna(denominator) or denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def safe_percentage(numerator: float, denominator: float) -> float:
    """
    Rigorous percentage calculation.
    Ensures 100.0 is only returned if values are mathematically equal (within 1e-09).
    Never rounds up to 100.0 to prevent misleading financial reporting.
    """
    if pd.isna(numerator) or pd.isna(denominator) or denominator <= 0:
        return 0.0

    val_n = float(numerator)
    val_d = float(denominator)

    if np.isclose(val_n, val_d, rtol=1e-09):
        return 100.0 if val_n > 0 else 0.0

    percentage = (val_n / val_d) * 100
    
    if percentage >= 100.0:
        return 99.99
        
    return min(float(percentage), 99.99)


def get_portfolio_share(value: float, total: float) -> float:
    """
    Calculates percentage share of a specific value against the total portfolio.
    """
    return safe_percentage(value, total)

def get_branch_share(value: float, branch_total: float) -> float:
    """
    Calculates percentage share of a value against a branch total.
    """
    return safe_percentage(value, branch_total)


def find_column_case_insensitive(df: pd.DataFrame, column_name: str) -> Optional[str]:
    """
    Find a column in the dataframe case-insensitively.
    Returns the actual column name if found, None otherwise.
    """
    if column_name in df.columns:
        return column_name
    
    for col in df.columns:
        if col.lower() == column_name.lower():
            return col
    return None


def get_arrears_time_series(
    df: pd.DataFrame,
    group_by: Optional[str] = None,
    date_col: str = 'Report_Date',
    value_col: str = 'Arrears',
    freq: str = 'D',
) -> pd.DataFrame:
    """
    Aggregate arrears over time.

    Args:
        df: Input dataframe containing a date column (usually `Report_Date`).
        group_by: Optional column to group by (e.g., 'Branch', 'Loan_Officer', 'AccountID').
        date_col: Name of the date column to use.
        value_col: Numeric value to aggregate (defaults to 'Arrears').
        freq: Resample frequency string (e.g., 'D', 'W', 'M').

    Returns:
        DataFrame with aggregated values indexed by period (and group if requested).
    """
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()

    ts = df.copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors='coerce')
    ts = ts.dropna(subset=[date_col])

    if group_by and group_by in ts.columns:
        grouped = ts.groupby([group_by, pd.Grouper(key=date_col, freq=freq)])[value_col].sum().reset_index()
        return grouped
    else:
        grouped = ts.groupby(pd.Grouper(key=date_col, freq=freq))[value_col].sum().reset_index()
        return grouped


def get_trend_for_entity(
    df: pd.DataFrame,
    entity_col: str,
    entity_value: str,
    date_col: str = 'Report_Date',
    value_col: str = 'Arrears',
    freq: str = 'D',
) -> pd.DataFrame:
    """
    Return a time series for a single entity (account, branch, or officer).
    """
    if df.empty:
        return pd.DataFrame()
    
    entity_col_actual = find_column_case_insensitive(df, entity_col) or entity_col
    date_col_actual = find_column_case_insensitive(df, date_col) or date_col
    value_col_actual = find_column_case_insensitive(df, value_col) or value_col
    
    if entity_col_actual not in df.columns:
        return pd.DataFrame()
    
    try:
        mask = df[entity_col_actual].astype(str) == str(entity_value)
        return get_arrears_time_series(df[mask], None, date_col=date_col_actual, value_col=value_col_actual, freq=freq)
    except Exception:
        return pd.DataFrame()


def get_top_movers(
    df: pd.DataFrame,
    group_by: str,
    date_col: str = 'Report_Date',
    value_col: str = 'Arrears',
    recent_period_days: int = 30,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Identify top movers (largest absolute increase) in `value_col` over the most recent period compared
    to the previous period of the same length.
    """
    if df.empty:
        return pd.DataFrame()
    
    group_col = find_column_case_insensitive(df, group_by) or group_by
    date_col_actual = find_column_case_insensitive(df, date_col) or date_col
    value_col_actual = find_column_case_insensitive(df, value_col) or value_col
    
    if group_col not in df.columns or date_col_actual not in df.columns or value_col_actual not in df.columns:
        return pd.DataFrame()

    try:
        ts = df.copy()
        ts[date_col_actual] = pd.to_datetime(ts[date_col_actual], errors='coerce')
        ts = ts.dropna(subset=[date_col_actual])

        latest = ts[date_col_actual].max()
        if pd.isna(latest):
            return pd.DataFrame()
        # Define recent period window (exclusive of previous window)
        recent_start = latest - pd.Timedelta(days=recent_period_days)
        previous_start = recent_start - pd.Timedelta(days=recent_period_days)

        # recent: (recent_start, latest]
        recent = ts[(ts[date_col_actual] > recent_start) & (ts[date_col_actual] <= latest)]
        # previous: (previous_start, recent_start]
        previous = ts[(ts[date_col_actual] > previous_start) & (ts[date_col_actual] <= recent_start)]

        recent_sum = recent.groupby(group_col)[value_col_actual].sum()
        previous_sum = previous.groupby(group_col)[value_col_actual].sum()

        combined = pd.concat([previous_sum, recent_sum], axis=1).fillna(0)
        combined.columns = ['previous_period', 'recent_period']
        combined['change'] = combined['recent_period'] - combined['previous_period']
        # percent change relative to previous_period; avoid division by zero
        combined['pct_change'] = combined['change'] / combined['previous_period'].replace(0, np.nan)
        combined = combined.reset_index().sort_values('change', ascending=False)
        combined['pct_change'] = combined['pct_change'].fillna(0.0)
        return combined.head(top_n)
    except Exception:
        return pd.DataFrame()


def calculate_par_percentage(df: pd.DataFrame) -> float:
    """
    Calculate Portfolio at Risk (PAR) percentage.
    PAR % = (Sum of Arrears for accounts with Days > 0) / Total Portfolio Principal × 100
    Handles missing columns gracefully with case-insensitive lookup.
    """
    if df.empty:
        return 0.0
    
    # Find columns with case-insensitive lookup
    arrears_col = find_column_case_insensitive(df, 'Arrears')
    days_col = find_column_case_insensitive(df, 'Days')
    principle_col = find_column_case_insensitive(df, 'Principle')
    total_balance_col = find_column_case_insensitive(df, 'TotalBalance')
    
    # Check if required columns exist
    if arrears_col is None or days_col is None:
        return 0.0
    
    # Deduplication check: Ensure we only count unique accounts if AccountID exists
    id_col = find_column_case_insensitive(df, 'AccountID')
    calc_df = df.drop_duplicates(subset=[id_col]) if id_col else df
    
    try:
        # Filter accounts with Days > 0 (in arrears)
        in_arrears_mask = (calc_df[days_col].notna()) & (calc_df[days_col] > 0)
        in_arrears = calc_df[in_arrears_mask]
        
        total_arrears = in_arrears[arrears_col].sum()
        
        # Get total portfolio
        if principle_col:
            total_portfolio = calc_df[principle_col].sum()
        elif total_balance_col:
            total_portfolio = calc_df[total_balance_col].sum()
        else:
            return 0.0
        
        return get_portfolio_share(total_arrears, total_portfolio)
    except Exception:
        return 0.0


def calculate_arrears_to_portfolio_ratio(df: pd.DataFrame, group_by: Optional[str] = None) -> pd.DataFrame:
    """
    Calculate arrears-to-portfolio ratio.
    Ratio = Arrears / Principle (or TotalBalance)
    
    Args:
        df: Input dataframe
        group_by: Column to group by (e.g., 'Branch', 'Loan_Officer', 'Product')
    
    Returns:
        DataFrame with ratios
    """
    if df.empty:
        return pd.DataFrame()
    
    # Find columns with case-insensitive lookup
    arrears_col = find_column_case_insensitive(df, 'Arrears')
    principle_col = find_column_case_insensitive(df, 'Principle')
    total_balance_col = find_column_case_insensitive(df, 'TotalBalance')
    
    if arrears_col is None:
        return pd.DataFrame()
    
    if group_by:
        group_col = find_column_case_insensitive(df, group_by) or group_by
        
        agg_dict = {arrears_col: 'sum'}
        if principle_col:
            agg_dict[principle_col] = 'sum'
        if total_balance_col:
            agg_dict[total_balance_col] = 'sum'
        
        try:
            grouped = df.groupby(group_col).agg(agg_dict).reset_index()
            
            # Use Principle if available, otherwise TotalBalance
            portfolio_col = principle_col if principle_col else total_balance_col
            
            if portfolio_col:
                grouped['Ratio'] = grouped.apply(lambda x: _safe_divide(x[arrears_col], x[portfolio_col]), axis=1)
            else:
                grouped['Ratio'] = 0.0 
            
            # Rename columns for consistency
            grouped = grouped.rename(columns={group_col: 'Product' if group_col == 'product' else group_col})
            
            return grouped.sort_values('Ratio', ascending=False)
        except Exception:
            return pd.DataFrame()
    else:
        try:
            total_arrears = df[arrears_col].sum()
            if principle_col:
                portfolio = df[principle_col].sum()
            elif total_balance_col:
                portfolio = df[total_balance_col].sum()
            else:
                portfolio = 0
            
            ratio = _safe_divide(total_arrears, portfolio)
            return pd.DataFrame({'Ratio': [ratio]})
        except Exception:
            return pd.DataFrame()


def classify_risk_ratio(ratio: float) -> str:
    """
    Categorize performance based on arrears-to-principal ratio.
    """
    if ratio >= 0.20:
        return "🔴 Critical"
    if ratio >= 0.10:
        return "🟠 High Risk"
    if ratio >= 0.05:
        return "🟡 Watchlist"
    return "🟢 Healthy"


def get_branch_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates branch performance based on Risk Ratio (Arrears/Principal)."""
    if df.empty: return pd.DataFrame()
    
    b_col = find_column_case_insensitive(df, 'Branch') or 'Branch'
    a_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    p_col = find_column_case_insensitive(df, 'Principle') or 'Principle'
    
    try:
        perf = df.groupby(b_col).agg({a_col: 'sum', p_col: 'sum'}).reset_index()
        perf.columns = ['Branch', 'Arrears', 'Principal']
        perf['Risk_Ratio'] = perf.apply(lambda x: _safe_divide(x['Arrears'], x['Principal']), axis=1)
        perf['Classification'] = perf['Risk_Ratio'].apply(classify_risk_ratio)
        return perf.sort_values('Risk_Ratio', ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_product_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates product performance based on Risk Ratio (Arrears/Principal)."""
    if df.empty: return pd.DataFrame()
    
    pr_col = find_column_case_insensitive(df, 'Product') or 'Product'
    a_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    p_col = find_column_case_insensitive(df, 'Principle') or 'Principle'
    
    try:
        perf = df.groupby(pr_col).agg({a_col: 'sum', p_col: 'sum'}).reset_index()
        perf.columns = ['Product', 'Arrears', 'Principal']
        perf['Risk_Ratio'] = perf.apply(lambda x: _safe_divide(x['Arrears'], x['Principal']), axis=1)
        perf['Classification'] = perf['Risk_Ratio'].apply(classify_risk_ratio)
        return perf.sort_values('Risk_Ratio', ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_officer_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates officer performance based on Risk Ratio (Arrears/Principal).
    Includes Branch context for organizational clarity.
    """
    if df.empty: return pd.DataFrame()

    o_col = find_column_case_insensitive(df, 'Loan_Officer') or 'Loan_Officer'
    b_col = find_column_case_insensitive(df, 'Branch') or 'Branch'
    a_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    p_col = find_column_case_insensitive(df, 'Principle') or 'Principle'

    try:
        perf = df.groupby([b_col, o_col]).agg({a_col: 'sum', p_col: 'sum'}).reset_index()
        perf.columns = ['Branch', 'Officer', 'Arrears', 'Principal']
        perf['Risk_Ratio'] = perf.apply(lambda x: _safe_divide(x['Arrears'], x['Principal']), axis=1)
        perf['Classification'] = perf['Risk_Ratio'].apply(classify_risk_ratio)
        return perf.sort_values('Risk_Ratio', ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_officer_ranking_split(df: pd.DataFrame, n: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Splits officers into best and worst performers based on Risk Ratio."""
    perf = get_officer_performance(df)
    if perf.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Worst are those with highest Risk Ratio
    worst = perf.nlargest(n, 'Risk_Ratio')
    # Best are those with lowest Risk Ratio (excluding 0 if many exist)
    best = perf.nsmallest(n, 'Risk_Ratio')
    
    return best, worst


def get_top_risk_branch(df: pd.DataFrame) -> Optional[Tuple[str, float]]:
    """Get branch with highest Risk Ratio."""
    perf = get_branch_performance(df)
    if perf.empty:
        return None
    
    top = perf.iloc[0]
    return (top['Branch'], top['Risk_Ratio'])


def get_top_risk_product(df: pd.DataFrame) -> Optional[Tuple[str, float]]:
    """Get product with highest Risk Ratio."""
    perf = get_product_performance(df)
    if perf.empty:
        return None
    
    top = perf.iloc[0]
    return (top['Product'], top['Risk_Ratio'])


def get_star_performers(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Get officers with lowest Risk Ratio."""
    perf = get_officer_performance(df)
    if perf.empty:
        return pd.DataFrame()
    return perf.nsmallest(top_n, 'Risk_Ratio').reset_index(drop=True)


def categorize_by_aging(df: pd.DataFrame) -> pd.DataFrame:
    """
    Categorize accounts by aging buckets.
    Returns dataframe with 'Aging_Bucket' column added.
    Handles case-insensitive 'Days' column lookup.
    """
    if df.empty:
        return df.copy()
    
    df = df.copy()
    
    days_col = find_column_case_insensitive(df, 'Days')
    if days_col is None:
        # If no Days column found, return with all Current
        df['Aging_Bucket'] = "Current"
        return df
    
    def assign_bucket(days):
        if pd.isna(days) or days is None:
            return "Current"
        try:
            days = int(days)
        except (ValueError, TypeError):
            return "Current"
        
        if days <= 30:
            return "Early Warning (1-30)"
        elif days <= 60:
            return "Moderate (31-60)"
        elif days <= 90:
            return "Warning (61-90)"
        else:
            return "Critical (>90)"
    
    df['Aging_Bucket'] = df[days_col].apply(assign_bucket)
    return df


def get_portfolio_distribution_by_aging(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate portfolio distribution by aging buckets.
    Returns dataframe with count, arrears amount, and percentage per bucket.
    """
    if df.empty:
        return pd.DataFrame()
    
    df_categorized = categorize_by_aging(df)
    
    # Find columns with case-insensitive lookup
    account_id_col = find_column_case_insensitive(df_categorized, 'AccountID')
    arrears_col = find_column_case_insensitive(df_categorized, 'Arrears')
    principle_col = find_column_case_insensitive(df_categorized, 'Principle')
    total_balance_col = find_column_case_insensitive(df_categorized, 'TotalBalance')
    
    try:
        # Group by aging bucket with dynamic column selection
        if account_id_col and arrears_col and principle_col and total_balance_col:
            distribution = df_categorized.groupby('Aging_Bucket').agg({
                account_id_col: 'count',
                arrears_col: 'sum',
                principle_col: 'sum',
                total_balance_col: 'sum'
            }).reset_index()
            
            distribution.columns = ['Aging_Bucket', 'Account_Count', 'Total_Arrears', 'Total_Principle', 'Total_Balance']
        else:
            return pd.DataFrame()
        
        # Calculate percentages
        if principle_col:
            total_portfolio = df_categorized[principle_col].sum()
        elif total_balance_col:
            total_portfolio = df_categorized[total_balance_col].sum()
        else:
            total_portfolio = 0
        
        distribution['Portfolio_Percentage'] = distribution['Total_Principle'].apply(lambda x: get_portfolio_share(x, total_portfolio))

        bucket_order = ["Current", "Early Warning (1-30)", "Moderate (31-60)", "Warning (61-90)", "Critical (>90)"]
        distribution['Order'] = distribution['Aging_Bucket'].apply(
            lambda x: bucket_order.index(x) if x in bucket_order else 999
        )
        distribution = distribution.sort_values('Order').drop('Order', axis=1)
        
        return distribution
    except Exception:
        return pd.DataFrame()


def get_branch_risk_percentage(df: pd.DataFrame, branch: str) -> float:
    """Calculate what percentage of total portfolio risk a branch holds."""
    if df.empty:
        return 0.0
    
    branch_col = find_column_case_insensitive(df, 'Branch')
    arrears_col = find_column_case_insensitive(df, 'Arrears')
    
    if branch_col is None or arrears_col is None:
        return 0.0
    
    try:
        branch_df = df[df[branch_col].astype(str).str.lower() == branch.lower()]
        total_arrears = df[arrears_col].sum()
        branch_arrears = branch_df[arrears_col].sum()
        
        return get_portfolio_share(branch_arrears, total_arrears)
    except Exception:
        return 0.0


def get_main_driver_product_in_branch(df: pd.DataFrame, branch: str) -> Optional[str]:
    """Get the product that is the main driver of arrears in a specific branch."""
    if df.empty:
        return None
    
    branch_col = find_column_case_insensitive(df, 'Branch')
    product_col = find_column_case_insensitive(df, 'Product')
    arrears_col = find_column_case_insensitive(df, 'Arrears')
    
    if branch_col is None or product_col is None or arrears_col is None:
        return None
    
    try:
        branch_df = df[df[branch_col].astype(str).str.lower() == branch.lower()]
        if branch_df.empty:
            return None
        
        product_totals = branch_df.groupby(product_col)[arrears_col].sum().sort_values(ascending=False)
        if product_totals.empty:
            return None
        
        return product_totals.index[0]
    except Exception:
        return None


def get_top_accounts_by_band(df: pd.DataFrame, band: str, top_n: int = 5) -> pd.DataFrame:
    """
    Get top N accounts by arrears amount in a specific aging band.
    
    Args:
        df: Input dataframe
        band: Aging band ('Early Warning', 'Moderate', 'Warning', 'Critical')
        top_n: Number of top accounts to return
    """
    if df.empty:
        return pd.DataFrame()
    
    df_categorized = categorize_by_aging(df)
    
    # Map band names to bucket names
    band_map = {
        'Early Warning': 'Early Warning (1-30)',
        'Moderate': 'Moderate (31-60)',
        'Warning': 'Warning (61-90)',
        'Critical': 'Critical (>90)'
    }
    
    bucket_name = band_map.get(band, band)
    band_df = df_categorized[df_categorized['Aging_Bucket'] == bucket_name]
    
    if band_df.empty:
        return pd.DataFrame()
    
    try:
        # Find columns with case-insensitive lookup
        account_id_col = find_column_case_insensitive(band_df, 'AccountID')
        branch_col = find_column_case_insensitive(band_df, 'Branch')
        officer_col = find_column_case_insensitive(band_df, 'Loan_Officer')
        product_col = find_column_case_insensitive(band_df, 'Product')
        arrears_col = find_column_case_insensitive(band_df, 'Arrears')
        days_col = find_column_case_insensitive(band_df, 'Days')
        principle_col = find_column_case_insensitive(band_df, 'Principle')
        
        # Build column list dynamically
        cols_to_select = []
        if account_id_col:
            cols_to_select.append(account_id_col)
        if branch_col:
            cols_to_select.append(branch_col)
        if officer_col:
            cols_to_select.append(officer_col)
        if product_col:
            cols_to_select.append(product_col)
        if arrears_col:
            cols_to_select.append(arrears_col)
        if days_col:
            cols_to_select.append(days_col)
        if principle_col:
            cols_to_select.append(principle_col)
        
        if not cols_to_select:
            return pd.DataFrame()
        
        # Sort by arrears descending
        if arrears_col:
            top_accounts = band_df.nlargest(top_n, arrears_col)[cols_to_select].copy()
        else:
            top_accounts = band_df[cols_to_select].copy().head(top_n)
        
        return top_accounts
    except Exception:
        return pd.DataFrame()


def get_priority_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get summary statistics for each priority band.
    Returns dataframe with count and total amount per band.
    """
    if df.empty:
        return pd.DataFrame()
    
    df_categorized = categorize_by_aging(df)
    
    # Find columns with case-insensitive lookup
    account_id_col = find_column_case_insensitive(df_categorized, 'AccountID')
    arrears_col = find_column_case_insensitive(df_categorized, 'Arrears')
    principle_col = find_column_case_insensitive(df_categorized, 'Principle')
    
    if not account_id_col or not arrears_col:
        return pd.DataFrame()
    
    try:
        agg_dict = {account_id_col: 'count', arrears_col: 'sum'}
        if principle_col:
            agg_dict[principle_col] = 'sum'
        
        summary = df_categorized.groupby('Aging_Bucket').agg(agg_dict).reset_index()
        
        # Rename columns
        summary.columns = ['Aging_Bucket', 'Account_Count', 'Total_Arrears', 'Total_Principle'] if principle_col else ['Aging_Bucket', 'Account_Count', 'Total_Arrears']
        
        # Map to priority names
        priority_map = {
            'Early Warning (1-30)': 'Early Warning',
            'Moderate (31-60)': 'Moderate',
            'Warning (61-90)': 'Warning',
            'Critical (>90)': 'Critical',
            'Current': 'Current'
        }
        
        summary['Priority'] = summary['Aging_Bucket'].map(priority_map).fillna('Unknown')
        
        return summary
    except Exception:
        return pd.DataFrame()


def get_branch_arrears_summary(df: pd.DataFrame) -> pd.Series:
    """Aggregates total arrears by branch for UI display."""
    branch_col = find_column_case_insensitive(df, 'Branch') or 'Branch'
    arrears_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    if df.empty: return pd.Series(dtype=float)
    return df.groupby(branch_col)[arrears_col].sum().sort_values(ascending=False)


def get_product_arrears_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates total arrears by product for UI display."""
    product_col = find_column_case_insensitive(df, 'Product') or 'Product'
    arrears_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    if df.empty: return pd.DataFrame()
    return df.groupby(product_col)[arrears_col].sum().reset_index()


def get_aging_arrears_summary(df: pd.DataFrame) -> pd.Series:
    """Aggregates total arrears by aging bucket for UI display."""
    arrears_col = find_column_case_insensitive(df, 'Arrears') or 'Arrears'
    if df.empty: return pd.Series(dtype=float)
    if 'Aging_Bucket' not in df.columns:
        return pd.Series(dtype=float)
    return df.groupby('Aging_Bucket')[arrears_col].sum()


def get_filtered_trend_data(df: pd.DataFrame, group_by: str, top_n: int = 10) -> pd.DataFrame:
    """Prepares trend data for plotting, ensuring ZERO math remains in the UI."""
    if df.empty or 'Report_Date' not in df.columns:
        return pd.DataFrame()
    
    df_trend = df.copy()
    df_trend['Report_Date'] = pd.to_datetime(df_trend['Report_Date'], errors='coerce')
    df_trend = df_trend.dropna(subset=['Report_Date'])
    
    group_col = find_column_case_insensitive(df_trend, group_by) or group_by
    trend_grp = df_trend.groupby([pd.Grouper(key='Report_Date', freq='D'), group_col])['Arrears'].sum().reset_index()
    
    if trend_grp[group_col].nunique() > top_n:
        totals = df_trend.groupby(group_col)['Arrears'].sum().nlargest(top_n)
        trend_grp = trend_grp[trend_grp[group_col].isin(totals.index)]
    return trend_grp


def get_standard_metrics_package(df_display: pd.DataFrame, df_full: pd.DataFrame) -> Dict[str, Any]:
    """
    Centralized aggregation logic to bundle metrics for AI interpretation.
    Enforces 'math-only' rule for calculations.py.
    """
    if df_display.empty:
        return {}

    arrears_col = find_column_case_insensitive(df_display, 'Arrears') or 'Arrears'
    days_col = find_column_case_insensitive(df_display, 'Days') or 'Days'
    principle_col = find_column_case_insensitive(df_display, 'Principle')
    total_balance_col = find_column_case_insensitive(df_display, 'TotalBalance')
    id_col = find_column_case_insensitive(df_display, 'AccountID')

    # Deduplicate for snapshot accuracy
    calc_df = df_display.drop_duplicates(subset=[id_col]) if id_col else df_display

    total_arrears = df_display[arrears_col].sum()
    
    if principle_col:
        total_portfolio = df_display[principle_col].sum()
    elif total_balance_col:
        total_portfolio = df_display[total_balance_col].sum()
    else:
        total_portfolio = 0
        
    accounts_in_arrears = len(df_display[df_display[days_col].notna() & (df_display[days_col] > 0)])
    avg_days = df_display[df_display[days_col].notna() & (df_display[days_col] > 0)][days_col].mean() or 0
    par_percentage = calculate_par_percentage(df_display)

    # Raw metrics only - Let agents interpret thresholds
    risk_metrics = {
        "par_percentage": round(float(par_percentage), 2),
        "avg_days_past_due": round(float(avg_days), 1),
        "exposure_amount": round(float(total_arrears), 2)
    }

    # Summaries
    officer_col = find_column_case_insensitive(df_display, 'Loan_Officer') or 'Loan_Officer'
    branch_col = find_column_case_insensitive(df_display, 'Branch') or 'Branch'
    date_col = find_column_case_insensitive(df_full, 'Report_Date')

    # Comprehensive Branch Risk Summary (All Branches)
    portfolio_col = principle_col if principle_col else total_balance_col
    if branch_col and arrears_col and portfolio_col:
        # Aggregate main metrics
        branch_stats = df_display.groupby(branch_col).agg({
            arrears_col: 'sum',
            portfolio_col: 'sum',
            days_col: 'mean'
        }).reset_index()
        branch_stats.columns = ['Branch', 'Arrears', 'Principal', 'Avg_Days']
        branch_stats['Risk_Ratio'] = branch_stats.apply(lambda x: _safe_divide(x['Arrears'], x['Principal']), axis=1)
        
        total_arrears_val = branch_stats['Arrears'].sum()
        branch_stats['Portfolio_Contribution'] = branch_stats['Arrears'].apply(lambda x: _safe_divide(x, total_arrears_val))
        branch_stats['Classification'] = branch_stats['Risk_Ratio'].apply(classify_risk_ratio)

        # Calculate Trend per Branch if historical data exists
        branch_stats['Trend'] = "→ stable"
        if date_col and not df_full.empty:
            try:
                latest_date = pd.to_datetime(df_full[date_col]).max()
                prev_date = latest_date - pd.Timedelta(days=1)
                
                current_snap = df_full[pd.to_datetime(df_full[date_col]) == latest_date].groupby(branch_col)[arrears_col].sum()
                prev_snap = df_full[pd.to_datetime(df_full[date_col]) == prev_date].groupby(branch_col)[arrears_col].sum()
                
                def get_direction(branch):
                    curr = current_snap.get(branch, 0)
                    prev = prev_snap.get(branch, 0)
                    if prev == 0: return "→ stable"
                    diff = (curr - prev) / prev
                    if diff > 0.01: return "↑ worsening"
                    if diff < -0.01: return "↓ improving"
                    return "→ stable"
                
                branch_stats['Trend'] = branch_stats['Branch'].apply(get_direction)
            except Exception:
                pass

        branch_stats = branch_stats.fillna(0)
        branch_risk_summary = branch_stats.to_dict(orient='records')
    else:
        branch_risk_summary = []

    officer_summary = df_display.groupby(officer_col)[arrears_col].sum().sort_values(ascending=False).head(10).to_dict()

    # Trend (using report date if available)
    recent_trend = {}
    date_col = find_column_case_insensitive(df_full, 'Report_Date')
    if date_col:
        recent_trend = (
            df_full.groupby(date_col)[arrears_col]
            .sum()
            .tail(7)
            .to_dict()
        )

    return {
        "total_arrears": round(float(total_arrears), 2),
        "total_portfolio": round(float(total_portfolio), 2),
        "accounts_in_arrears": int(accounts_in_arrears),
        "average_days_past_due": round(float(avg_days), 1),
        "par_percentage": round(float(par_percentage), 2),
        "risk_metrics": risk_metrics,
        "officer_summary": officer_summary,
        "branch_risk_summary": branch_risk_summary,
        "recent_trend": recent_trend
    }
