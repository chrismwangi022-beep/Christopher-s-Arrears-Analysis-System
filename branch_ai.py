"""
Spread Capital Limited — Branch Intelligence Engine
src/branch_ai.py

Deterministic, rule-based interpretation of branch performance.
"""
import streamlit as st
import pandas as pd
from src.calculations import find_column_case_insensitive, _safe_divide, classify_risk_ratio
from src.constants import CURRENCY_SYMBOL, COLORS

def render_branch_intelligence(df_display: pd.DataFrame, df_full: pd.DataFrame, selected_branches: list):
    """Primary entry point to render the dynamic Branch Intelligence Engine."""
    st.subheader("🏢 Branch Intelligence Engine")
    
    # Detect columns
    b_col = find_column_case_insensitive(df_display, 'Branch') or 'Branch'
    a_col = find_column_case_insensitive(df_display, 'Arrears') or 'Arrears'
    p_col = find_column_case_insensitive(df_display, 'Principle') or 'Principle'
    d_col = find_column_case_insensitive(df_display, 'Days') or 'Days'
    pr_col = find_column_case_insensitive(df_display, 'Product') or 'Product'
    date_col = find_column_case_insensitive(df_full, 'Report_Date')

    # Aggregate metrics for the current selection
    branch_stats = df_display.groupby(b_col).agg({
        a_col: 'sum',
        p_col: 'sum',
        d_col: 'mean'
    }).reset_index()
    branch_stats.columns = ['Branch', 'Arrears', 'Principal', 'Avg_DPD']
    branch_stats['Risk_Ratio'] = branch_stats.apply(lambda x: _safe_divide(x['Arrears'], x['Principal']), axis=1)
    branch_stats['Status'] = branch_stats['Risk_Ratio'].apply(classify_risk_ratio)
    
    # Determine mode
    unique_branches = branch_stats['Branch'].unique()
    is_all = "All" in selected_branches or len(selected_branches) == 0 or len(unique_branches) > 5

    if len(unique_branches) == 1:
        _render_single_branch_intel(branch_stats.iloc[0], df_display, df_full, b_col, a_col, pr_col, date_col)
    elif not is_all:
        _render_multi_branch_intel(branch_stats)
    else:
        _render_portfolio_branch_intel(branch_stats)

def _render_single_branch_intel(stats, df_branch, df_full, b_col, a_col, pr_col, date_col):
    """Detailed deep-dive for a single selected branch."""
    branch_name = str(stats['Branch']).title()
    
    # 1. Trend Calculation
    trend_str = "→ stable"
    if date_col:
        dates = sorted(pd.to_datetime(df_full[date_col]).unique())
        if len(dates) >= 2:
            curr_val = df_full[pd.to_datetime(df_full[date_col]) == dates[-1]][df_full[b_col] == stats['Branch']][a_col].sum()
            prev_val = df_full[pd.to_datetime(df_full[date_col]) == dates[-2]][df_full[b_col] == stats['Branch']][a_col].sum()
            if prev_val > 0:
                diff = (curr_val - prev_val) / prev_val
                if diff > 0.01: trend_str = "↑ worsening"
                elif diff < -0.01: trend_str = "↓ improving"

    # 2. Dominant Product
    top_prod = df_branch.groupby(pr_col)[a_col].sum().idxmax() if not df_branch.empty else "N/A"
    
    # 3. Concentration (Share of display total)
    total_display_arrears = df_branch[a_col].sum()
    
    st.info(f"**Intelligence Snapshot: {branch_name}**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Current Outlook:** {stats['Status']}")
        st.markdown(f"- **Portfolio Quality:** {stats['Risk_Ratio']:.1%} Risk Ratio")
        st.markdown(f"- **Arrears Trend:** {trend_str}")
        st.markdown(f"- **Recovery Pressure:** {'🔴 High' if stats['Avg_DPD'] > 60 else '🟡 Moderate' if stats['Avg_DPD'] > 30 else '🟢 Low'} ({stats['Avg_DPD']:.1f} avg days)")
    with col2:
        st.markdown("**Risk Drivers:**")
        st.markdown(f"- **Dominant Product:** {top_prod}")
        st.markdown(f"- **Concentration:** {branch_name} holds {CURRENCY_SYMBOL} {stats['Arrears']:,.0f} in active arrears.")
        st.markdown(f"- **Strategic Focus:** {'Halt disbursements' if stats['Risk_Ratio'] >= 0.20 else 'Intensify field visits' if stats['Risk_Ratio'] >= 0.10 else 'Routine Monitoring'}")

def _render_multi_branch_intel(stats):
    """Comparison engine for 2-5 branches."""
    best = stats.nsmallest(1, 'Risk_Ratio').iloc[0]
    worst = stats.nlargest(1, 'Risk_Ratio').iloc[0]
    
    st.warning("**Comparative Branch Intelligence**")
    
    st.markdown(f"**Performance Gap:** There is a **{(worst['Risk_Ratio'] - best['Risk_Ratio']):.1%}** quality variance between the strongest and weakest selected branches.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"✅ **Strongest Portfolio:** {str(best['Branch']).title()}")
        st.markdown(f"- Ratio: {best['Risk_Ratio']:.1%} ({best['Status']})")
    with col2:
        st.markdown(f"⚠️ **Weakest Portfolio:** {str(worst['Branch']).title()}")
        st.markdown(f"- Ratio: {worst['Risk_Ratio']:.1%} ({worst['Status']})")
    
    # List remaining gaps
    if len(stats) > 2:
        with st.expander("View Delinquency Severity Ranking"):
            for _, row in stats.sort_values('Risk_Ratio', ascending=False).iterrows():
                st.write(f"- {str(row['Branch']).title()}: {row['Risk_Ratio']:.1%} — {row['Status']}")

def _render_portfolio_branch_intel(stats):
    """Aggregated portfolio-wide branch clustering and concentration analysis."""
    total_arr = stats['Arrears'].sum()
    stats['Exposure_Share'] = stats['Arrears'] / total_arr if total_arr > 0 else 0
    
    st.success("**Portfolio Branch Intelligence**")
    
    # Risk Clustering
    clusters = stats['Status'].value_counts()
    cluster_str = " | ".join([f"{k}: {v}" for k, v in clusters.items()])
    st.markdown(f"**Risk Clustering:** {cluster_str}")

    m1, m2 = st.columns(2)
    with m1:
        top_exp = stats.nlargest(1, 'Exposure_Share').iloc[0]
        st.markdown("**Concentration Exposure:**")
        st.markdown(f"- **{str(top_exp['Branch']).title()}** is the primary exposure hub, carrying **{top_exp['Exposure_Share']:.1%}** of total arrears volume.")
    
    with m2:
        critical_count = len(stats[stats['Risk_Ratio'] >= 0.10])
        st.markdown("**Systemic Health:**")
        st.markdown(f"- **{critical_count}** branches are currently exceeding the 10% High Risk threshold.")

    with st.expander("Executive Performance Summary"):
        best_3 = stats.nsmallest(3, 'Risk_Ratio')
        worst_3 = stats.nlargest(3, 'Risk_Ratio')
        
        c_a, c_b = st.columns(2)
        c_a.write("**Top 3 (Quality)**")
        for _, r in best_3.iterrows(): c_a.caption(f"{str(r['Branch']).title()}: {r['Risk_Ratio']:.1%}")
        
        c_b.write("**Bottom 3 (Risk)**")
        for _, r in worst_3.iterrows(): c_b.caption(f"{str(r['Branch']).title()}: {r['Risk_Ratio']:.1%}")