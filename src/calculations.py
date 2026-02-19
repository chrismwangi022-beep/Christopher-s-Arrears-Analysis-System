"""
Calculation functions for PAR, ratios, and risk rankings
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from .constants import AGING_BUCKETS

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
    if df.empty or entity_col not in df.columns:
        return pd.DataFrame()
    mask = df[entity_col].astype(str) == str(entity_value)
    return get_arrears_time_series(df[mask], None, date_col=date_col, value_col=value_col, freq=freq)


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
    if df.empty or group_by not in df.columns or date_col not in df.columns:
        return pd.DataFrame()

    ts = df.copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors='coerce')
    ts = ts.dropna(subset=[date_col])

    latest = ts[date_col].max()
    if pd.isna(latest):
        return pd.DataFrame()
    # Define recent period window (exclusive of previous window)
    recent_start = latest - pd.Timedelta(days=recent_period_days)
    previous_start = recent_start - pd.Timedelta(days=recent_period_days)

    # recent: (recent_start, latest]
    recent = ts[(ts[date_col] > recent_start) & (ts[date_col] <= latest)]
    # previous: (previous_start, recent_start]
    previous = ts[(ts[date_col] > previous_start) & (ts[date_col] <= recent_start)]

    recent_sum = recent.groupby(group_by)[value_col].sum()
    previous_sum = previous.groupby(group_by)[value_col].sum()

    combined = pd.concat([previous_sum, recent_sum], axis=1).fillna(0)
    combined.columns = ['previous_period', 'recent_period']
    combined['change'] = combined['recent_period'] - combined['previous_period']
    # percent change relative to previous_period; avoid division by zero
    combined['pct_change'] = combined['change'] / combined['previous_period'].replace(0, np.nan)
    combined = combined.reset_index().sort_values('change', ascending=False)
    combined['pct_change'] = combined['pct_change'].fillna(0.0)
    return combined.head(top_n)


def calculate_par_percentage(df: pd.DataFrame) -> float:
    """
    Calculate Portfolio at Risk (PAR) percentage.
    PAR % = (Sum of Arrears for accounts with Days > 0) / Total Portfolio × 100
    Handles missing columns gracefully.
    """
    if df.empty:
        return 0.0
    
    # Check if required columns exist
    if 'Days' not in df.columns or 'Arrears' not in df.columns:
        return 0.0
    
    # Filter accounts with Days > 0 (in arrears)
    in_arrears = df[df['Days'].notna() & (df['Days'] > 0)]
    
    total_arrears = in_arrears['Arrears'].sum()
    total_portfolio = df['Principle'].sum() if 'Principle' in df.columns else (df['TotalBalance'].sum() if 'TotalBalance' in df.columns else 0)
    
    if total_portfolio == 0:
        return 0.0
    
    return (total_arrears / total_portfolio) * 100


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
    
    if group_by:
        grouped = df.groupby(group_by).agg({
            'Arrears': 'sum',
            'Principle': 'sum',
            'TotalBalance': 'sum'
        }).reset_index()
        
        # Use Principle if available, otherwise TotalBalance
        portfolio_col = 'Principle' if 'Principle' in grouped.columns else 'TotalBalance'
        grouped['Ratio'] = grouped['Arrears'] / grouped[portfolio_col].replace(0, np.nan)
        grouped['Ratio'] = grouped['Ratio'].fillna(0.0)
        
        return grouped.sort_values('Ratio', ascending=False)
    else:
        total_arrears = df['Arrears'].sum()
        portfolio = df['Principle'].sum() if 'Principle' in df.columns else df['TotalBalance'].sum()
        ratio = total_arrears / portfolio if portfolio > 0 else 0.0
        return pd.DataFrame({'Ratio': [ratio]})


def get_top_risk_branch(df: pd.DataFrame) -> Optional[Tuple[str, float]]:
    """Get branch with highest total arrears."""
    if df.empty or 'Branch' not in df.columns or 'Arrears' not in df.columns:
        return None
    
    try:
        branch_totals = df.groupby('Branch')['Arrears'].sum().sort_values(ascending=False)
        if branch_totals.empty:
            return None
        
        top_branch = branch_totals.index[0]
        top_amount = branch_totals.iloc[0]
        return (top_branch, top_amount)
    except Exception:
        return None


def get_top_risk_product(df: pd.DataFrame) -> Optional[Tuple[str, float]]:
    """Get product with highest arrears-to-portfolio ratio."""
    if df.empty or 'Product' not in df.columns:
        return None
    
    product_ratios = calculate_arrears_to_portfolio_ratio(df, group_by='Product')
    if product_ratios.empty:
        return None
    
    top_product = product_ratios.iloc[0]['Product']
    top_ratio = product_ratios.iloc[0]['Ratio']
    return (top_product, top_ratio)


def get_star_performers(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Get officers with lowest arrears-to-portfolio ratio (top performers)."""
    if df.empty or 'Loan_Officer' not in df.columns:
        return pd.DataFrame()
    
    officer_ratios = calculate_arrears_to_portfolio_ratio(df, group_by='Loan_Officer')
    if officer_ratios.empty:
        return pd.DataFrame()
    
    # Sort ascending (lowest ratio = best performer)
    officer_ratios = officer_ratios.sort_values('Ratio', ascending=True)
    
    return officer_ratios.head(top_n)


def get_officer_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get arrears-to-portfolio performance for each loan officer.
    Higher ratio = needs improvement, lower ratio = star performer.
    """
    if df.empty or 'Loan_Officer' not in df.columns:
        return pd.DataFrame()
    
    perf = calculate_arrears_to_portfolio_ratio(df, group_by='Loan_Officer')
    if perf.empty:
        return pd.DataFrame()
    
    # Clean officer names for display
    perf = perf.rename(columns={'Loan_Officer': 'Officer'})
    perf['Officer'] = perf['Officer'].astype(str).str.title()
    
    return perf


def categorize_by_aging(df: pd.DataFrame) -> pd.DataFrame:
    """
    Categorize accounts by aging buckets.
    Returns dataframe with 'Aging_Bucket' column added.
    """
    df = df.copy()
    
    def assign_bucket(days):
        if pd.isna(days) or days is None:
            return "Current"
        days = int(days)
        if days <= 30:
            return "Early Warning (1-30)"
        elif days <= 60:
            return "Moderate (31-60)"
        elif days <= 90:
            return "Warning (61-90)"
        else:
            return "Critical (>90)"
    
    df['Aging_Bucket'] = df['Days'].apply(assign_bucket)
    return df


def get_portfolio_distribution_by_aging(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate portfolio distribution by aging buckets.
    Returns dataframe with count, arrears amount, and percentage per bucket.
    """
    df_categorized = categorize_by_aging(df)
    
    # Group by aging bucket
    distribution = df_categorized.groupby('Aging_Bucket').agg({
        'AccountID': 'count',
        'Arrears': 'sum',
        'Principle': 'sum',
        'TotalBalance': 'sum'
    }).reset_index()
    
    distribution.columns = ['Aging_Bucket', 'Account_Count', 'Total_Arrears', 'Total_Principle', 'Total_Balance']
    
    # Calculate percentages
    total_portfolio = df['Principle'].sum() if 'Principle' in df.columns else df['TotalBalance'].sum()
    if total_portfolio > 0:
        distribution['Portfolio_Percentage'] = (distribution['Total_Principle'] / total_portfolio) * 100
    else:
        distribution['Portfolio_Percentage'] = 0.0
    
    # Sort by aging severity (custom order)
    bucket_order = ["Current", "Early Warning (1-30)", "Moderate (31-60)", "Warning (61-90)", "Critical (>90)"]
    distribution['Order'] = distribution['Aging_Bucket'].apply(
        lambda x: bucket_order.index(x) if x in bucket_order else 999
    )
    distribution = distribution.sort_values('Order').drop('Order', axis=1)
    
    return distribution


def get_branch_risk_percentage(df: pd.DataFrame, branch: str) -> float:
    """Calculate what percentage of total portfolio risk a branch holds."""
    if df.empty or 'Branch' not in df.columns:
        return 0.0
    
    branch_df = df[df['Branch'].str.lower() == branch.lower()]
    total_arrears = df['Arrears'].sum()
    branch_arrears = branch_df['Arrears'].sum()
    
    if total_arrears == 0:
        return 0.0
    
    return (branch_arrears / total_arrears) * 100


def get_main_driver_product_in_branch(df: pd.DataFrame, branch: str) -> Optional[str]:
    """Get the product that is the main driver of arrears in a specific branch."""
    if df.empty or 'Branch' not in df.columns or 'Product' not in df.columns:
        return None
    
    branch_df = df[df['Branch'].str.lower() == branch.lower()]
    if branch_df.empty:
        return None
    
    product_totals = branch_df.groupby('Product')['Arrears'].sum().sort_values(ascending=False)
    if product_totals.empty:
        return None
    
    return product_totals.index[0]


def get_top_accounts_by_band(df: pd.DataFrame, band: str, top_n: int = 5) -> pd.DataFrame:
    """
    Get top N accounts by arrears amount in a specific aging band.
    
    Args:
        df: Input dataframe
        band: Aging band ('Early Warning', 'Moderate', 'Warning', 'Critical')
        top_n: Number of top accounts to return
    """
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
    
    # Sort by arrears descending
    top_accounts = band_df.nlargest(top_n, 'Arrears')[
        ['AccountID', 'Branch', 'Loan_Officer', 'Product', 'Arrears', 'Days', 'Principle']
    ].copy()
    
    return top_accounts


def get_priority_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get summary statistics for each priority band.
    Returns dataframe with count and total amount per band.
    """
    df_categorized = categorize_by_aging(df)
    
    summary = df_categorized.groupby('Aging_Bucket').agg({
        'AccountID': 'count',
        'Arrears': 'sum',
        'Principle': 'sum'
    }).reset_index()
    
    summary.columns = ['Aging_Bucket', 'Account_Count', 'Total_Arrears', 'Total_Principle']
    
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
