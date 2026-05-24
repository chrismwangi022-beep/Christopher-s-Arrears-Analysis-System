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
    st.subheader("🏢 Branch-Specific Insights")
    
    # Detect columns
    b_col = find_column_case_insensitive(df_display, 'Branch') or 'Branch'
    a_col = find_column_case_insensitive(df_display, 'Arrears') or 'Arrears'
    p_col = find_column_case_insensitive(df_display, 'Principle') or 'Principle'
    d_col = find_column_case_insensitive(df_display, 'Days') or 'Days'
    pr_col = find_column_case_insensitive(df_display, 'Product') or 'Product'
    date_col = find_column_case_insensitive(df_full, 'Report_Date')

    # Aggregate metrics for the current selection
    total_portfolio_arrears = df_full[a_col].sum() if not df_full.empty else 0
    branch_stats = df_display.groupby(b_col).agg({
        a_col: 'sum',
        p_col: 'sum',
        d_col: 'mean'
    }).reset_index()
    branch_stats.columns = ['Branch', 'Arrears', 'Principal', 'Avg_DPD']
    
    # Banking-Grade Calculations
    branch_stats['Risk_Ratio'] = branch_stats.apply(lambda x: _safe_divide(x['Arrears'], x['Principal']), axis=1)
    branch_stats['Contribution_Pct'] = branch_stats['Arrears'] / total_portfolio_arrears if total_portfolio_arrears > 0 else 0
    branch_stats['Status'] = branch_stats['Risk_Ratio'].apply(classify_risk_ratio)
    branch_stats['Rank'] = branch_stats['Risk_Ratio'].rank(ascending=False).astype(int)
    
    # Determine mode
    unique_branches = branch_stats['Branch'].unique()
    is_all = "All" in selected_branches or len(selected_branches) == 0 or len(unique_branches) > 5

    if len(unique_branches) == 1:
        _render_single_branch_intel(branch_stats.iloc[0], df_display, df_full, b_col, a_col, pr_col, date_col, total_portfolio_arrears)
    elif not is_all:
        _render_multi_branch_intel(branch_stats)
    else:
        _render_portfolio_branch_intel(branch_stats, df_full, b_col, a_col, date_col)

def _render_single_branch_intel(stats, df_branch, df_full, b_col, a_col, pr_col, date_col, total_global_arrears):
    """Detailed deep-dive for a single selected branch."""
    branch_name = str(stats['Branch']).title()
    
    # 1. Trend Calculation & Deterioration
    trend_str = "→ stable"
    severity_interpretation = "Healthy"
    if date_col:
        dates = sorted(pd.to_datetime(df_full[date_col]).unique())
        if len(dates) >= 2:
            curr_val = df_full[pd.to_datetime(df_full[date_col]) == dates[-1]][df_full[b_col] == stats['Branch']][a_col].sum()
            prev_val = df_full[pd.to_datetime(df_full[date_col]) == dates[-2]][df_full[b_col] == stats['Branch']][a_col].sum()
            if prev_val > 0:
                diff = (curr_val - prev_val) / prev_val
                if diff > 0.01: trend_str = "↑ worsening"
                elif diff < -0.01: trend_str = "↓ improving"

    # 2. Severity Interpretation
    if stats['Avg_DPD'] > 90: severity_interpretation = "🔴 Critical Loss Potential"
    elif stats['Avg_DPD'] > 60: severity_interpretation = "🟠 Impaired Recovery"
    elif stats['Avg_DPD'] > 30: severity_interpretation = "🟡 Collection Friction"
    else: severity_interpretation = "🟢 Early Delinquency"

    # 2. Dominant Product
    product_agg = df_branch.groupby(pr_col)[a_col].sum().sort_values(ascending=False)
    top_prod = product_agg.index[0] if not product_agg.empty else "N/A"
    prod_concentration = (product_agg.iloc[0] / stats['Arrears']) if stats['Arrears'] > 0 else 0
    
    st.info(f"### 🏢 {branch_name} Branch Analysis")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risk Concentration", f"{stats['Contribution_Pct']:.1%}", help="Branch contribution to total company arrears.")
    m2.metric("Arrears/Principal", f"{stats['Risk_Ratio']:.1%}", help="Delinquency relative to total disbursed portfolio.")
    m3.metric("Delinquency Severity", f"{stats['Avg_DPD']:.1f} Days", help="Average age of active arrears.")
    m4.metric("Status", stats['Status'].split()[-1])

    st.markdown(f"""
**📌 Executive Analytical Insight:**
{branch_name} branch shows a **{stats['Contribution_Pct']:.1%}** contribution to total portfolio risk. High arrears combined with elevated average delinquency days (**{stats['Avg_DPD']:.1f} days**) suggests weakened recovery velocity and increased probability of roll-forward into higher PAR buckets.

**🔍 Risk Indicators:**
- **Operational Status:** {severity_interpretation}
- **Product Concentration:** **{top_prod}** (accounts for {prod_concentration:.1%} of branch arrears)
- **Trend Profile:** {trend_str}

**🛠️ Recommended Priority:**
{'🚨 Immediate legal escalation & asset recovery for core delinquent accounts.' if stats['Avg_DPD'] > 60 else '📞 Intensify telephone follow-ups and guarantor engagement to normalize payments.' if stats['Avg_DPD'] > 30 else '✅ Maintain routine monitoring and early-warning SMS triggers.'}
""")

def _render_multi_branch_intel(stats):
    """Comparison engine for 2-5 branches."""
    best_branch = stats.nsmallest(1, 'Risk_Ratio').iloc[0]
    worst_branch = stats.nlargest(1, 'Risk_Ratio').iloc[0]
    
    st.warning("### 📊 Multi-Branch Comparative Intelligence")
    
    st.markdown(f"**Analytical Summary:** A quality variance of **{(worst_branch['Risk_Ratio'] - best_branch['Risk_Ratio']):.1%}** exists across the selection, indicating significant risk dispersion. Exposure imbalance is primarily driven by **{worst_branch['Branch'].title()}**.")

    # Ranking Table
    display_stats = stats[['Branch', 'Arrears', 'Principal', 'Risk_Ratio', 'Avg_DPD', 'Status']].sort_values('Risk_Ratio', ascending=False)
    st.dataframe(
        display_stats.style.format({
            'Arrears': f'{CURRENCY_SYMBOL} {{:,.0f}}',
            'Principal': f'{CURRENCY_SYMBOL} {{:,.0f}}',
            'Risk_Ratio': '{:.2%}',
            'Avg_DPD': '{:.1f}'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown(f"""
**🛠️ Recovery Prioritization:**
Resources should be reallocated to **{worst_branch['Branch'].title()}** to mitigate systemic spillover. **{best_branch['Branch'].title()}** serves as the internal benchmark for credit quality control.
""")

def _render_portfolio_branch_intel(stats, df_full, b_col, a_col, date_col):
    """Aggregated portfolio-wide branch clustering and concentration analysis."""
    st.success("### 🌐 Portfolio-Wide Branch Intelligence")
    
    # Identify Movers
    fastest_deteriorating = "N/A"
    healthiest = stats.nsmallest(1, 'Risk_Ratio').iloc[0]['Branch'].title()
    highest_risk = stats.nlargest(1, 'Risk_Ratio').iloc[0]['Branch'].title()
    highest_exposure = stats.nlargest(1, 'Arrears').iloc[0]
    
    if date_col:
        dates = sorted(pd.to_datetime(df_full[date_col]).unique())
        if len(dates) >= 2:
            curr = df_full[pd.to_datetime(df_full[date_col]) == dates[-1]].groupby(b_col)[a_col].sum()
            prev = df_full[pd.to_datetime(df_full[date_col]) == dates[-2]].groupby(b_col)[a_col].sum()
            delta = (curr - prev) / prev.replace(0, 1)
            fastest_deteriorating = delta.idxmax().title() if not delta.empty else "N/A"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Highest Risk", highest_risk)
    c2.metric("Fastest Worsening", fastest_deteriorating)
    c3.metric("Healthiest", healthiest)
    c4.metric("Top Exposure Hub", highest_exposure['Branch'].title())

    # Ranking Table with Banking Metrics
    st.markdown("#### 📊 Branch Ranking Position (By Risk Ratio)")
    rank_df = stats[['Rank', 'Branch', 'Arrears', 'Principal', 'Risk_Ratio', 'Contribution_Pct', 'Avg_DPD']].sort_values('Rank')
    st.dataframe(
        rank_df.style.format({
            'Arrears': f'{CURRENCY_SYMBOL} {{:,.0f}}',
            'Principal': f'{CURRENCY_SYMBOL} {{:,.0f}}',
            'Risk_Ratio': '{:.2%}',
            'Contribution_Pct': '{:.1%}',
            'Avg_DPD': '{:.1f}'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Executive Commentary
    critical_count = len(stats[stats['Risk_Ratio'] >= 0.10])
    concentration_val = highest_exposure['Arrears'] / stats['Arrears'].sum() if stats['Arrears'].sum() > 0 else 0
    
    st.markdown(f"""
#### 🧠 Executive Credit Commentary

**⚖️ Concentration Risk:**
The portfolio demonstrates significant risk concentration in **{highest_exposure['Branch'].title()}**, which alone accounts for **{concentration_val:.1%}** of the total arrears volume. Any deterioration in this single hub poses a systemic threat to overall PAR targets.

**📈 Branch Imbalance:**
Currently, **{critical_count}** branches have exceeded the 10% High-Risk threshold. The variance in delinquency severity (Avg DPD) suggests uneven collection performance or localized economic impact rather than a global product failure.

**🎯 Collection Prioritization:**
Operational focus must prioritize the **{fastest_deteriorating}** branch to arrest further slippage. Resources should be shifted from healthier clusters (e.g., **{healthiest}**) to critical hubs where roll-forward rates are highest.

**⚠️ Operational Concerns:**
Branches with Risk Ratios above 20% (e.g., **{highest_risk}**) should undergo an immediate credit process audit to identify if current arrears are a result of aggressive disbursement or weak field follow-up.
""")