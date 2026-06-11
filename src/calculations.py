"""
Calculation functions for PAR, ratios, and risk rankings
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from .constants import AGING_BUCKETS


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
    except Exception as e:
        print(f"Error calculating top movers: {e}")
        return pd.DataFrame()


def calculate_par_percentage(df: pd.DataFrame) -> float:
    """
    Calculate Portfolio at Risk (PAR) percentage.
    PAR % = (Sum of Arrears for accounts with Days > 0) / Total Portfolio × 100
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
    
    try:
        # Filter accounts with Days > 0 (in arrears)
        in_arrears = df[df[days_col].notna() & (df[days_col] > 0)]
        
        total_arrears = in_arrears[arrears_col].sum()
        
        # Get total portfolio
        if principle_col:
            total_portfolio = df[principle_col].sum()
        elif total_balance_col:
            total_portfolio = df[total_balance_col].sum()
        else:
            return 0.0
        
        if total_portfolio == 0:
            return 0.0
        
        return (total_arrears / total_portfolio) * 100
    except Exception as e:
        print(f"Error calculating PAR percentage: {e}")
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
                grouped['Ratio'] = grouped[arrears_col] / grouped[portfolio_col].replace(0, np.nan)
                grouped['Ratio'] = grouped['Ratio'].fillna(0.0)
            else:
                grouped['Ratio'] = 0.0
            
            # Rename columns for consistency
            grouped = grouped.rename(columns={group_col: 'Product' if group_col == 'product' else group_col})
            
            return grouped.sort_values('Ratio', ascending=False)
        except Exception as e:
            print(f"Error calculating arrears to portfolio ratio: {e}")
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
            
            ratio = total_arrears / portfolio if portfolio > 0 else 0.0
            return pd.DataFrame({'Ratio': [ratio]})
        except Exception as e:
            print(f"Error calculating ratio: {e}")
            return pd.DataFrame()


def get_top_risk_branch(df: pd.DataFrame) -> Optional[Tuple[str, float]]:
    """Get branch with highest total arrears."""
    if df.empty:
        return None
    
    branch_col = find_column_case_insensitive(df, 'Branch')
    arrears_col = find_column_case_insensitive(df, 'Arrears')
    
    if branch_col is None or arrears_col is None:
        return None
    
    try:
        branch_totals = df.groupby(branch_col)[arrears_col].sum().sort_values(ascending=False)
        if branch_totals.empty:
            return None
        
        top_branch = branch_totals.index[0]
        top_amount = branch_totals.iloc[0]
        return (top_branch, top_amount)
    except Exception:
        return None


def get_top_risk_product(df: pd.DataFrame) -> Optional[Tuple[str, float]]:
    """Get product with highest arrears-to-portfolio ratio."""
    if df.empty:
        return None
    
    product_col = find_column_case_insensitive(df, 'Product')
    if product_col is None:
        return None
    
    try:
        product_ratios = calculate_arrears_to_portfolio_ratio(df, group_by=product_col)
        if product_ratios.empty:
            return None
        
        top_product = product_ratios.iloc[0]['Product']
        top_ratio = product_ratios.iloc[0]['Ratio']
        return (top_product, top_ratio)
    except Exception:
        return None


def get_star_performers(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Get officers with lowest arrears-to-portfolio ratio (top performers)."""
    if df.empty:
        return pd.DataFrame()
    
    officer_col = find_column_case_insensitive(df, 'Loan_Officer')
    if officer_col is None:
        return pd.DataFrame()
    
    try:
        officer_ratios = calculate_arrears_to_portfolio_ratio(df, group_by=officer_col)
        if officer_ratios.empty:
            return pd.DataFrame()
        
        # Sort ascending (lowest ratio = best performer)
        officer_ratios = officer_ratios.sort_values('Ratio', ascending=True)
        
        return officer_ratios.head(top_n)
    except Exception:
        return pd.DataFrame()


def get_officer_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get arrears-to-portfolio performance for each loan officer.
    Higher ratio = needs improvement, lower ratio = star performer.
    """
    if df.empty:
        return pd.DataFrame()
    
    officer_col = find_column_case_insensitive(df, 'Loan_Officer')
    if officer_col is None:
        return pd.DataFrame()
    
    try:
        perf = calculate_arrears_to_portfolio_ratio(df, group_by=officer_col)
        if perf.empty:
            return pd.DataFrame()
        
        # Clean officer names for display
        perf = perf.rename(columns={officer_col: 'Officer'})
        perf['Officer'] = perf['Officer'].astype(str).str.title()
        
        return perf.sort_values('Ratio', ascending=False)
    except Exception as e:
        print(f"Error calculating officer performance: {e}")
        return pd.DataFrame()
    
    return perf


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
            total_portfolio = df[principle_col].sum()
        elif total_balance_col:
            total_portfolio = df[total_balance_col].sum()
        else:
            total_portfolio = 0
        
        if total_portfolio > 0 and 'Total_Principle' in distribution.columns:
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
    except Exception as e:
        print(f"Error calculating portfolio distribution by aging: {e}")
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
        
        if total_arrears == 0:
            return 0.0
        
        return (branch_arrears / total_arrears) * 100
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
    except Exception as e:
        print(f"Error getting top accounts by band: {e}")
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
    except Exception as e:
        print(f"Error getting priority band summary: {e}")
        return pd.DataFrame()
