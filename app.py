"""
Spread Capital Arrears Analysis System
Main Streamlit Application
Cloud-Ready with Google Drive Integration
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import io

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import load_all_data
from src.google_drive_handler import get_drive_handler
from src.calculations import (
    calculate_par_percentage,
    get_top_risk_branch,
    get_top_risk_product,
    get_star_performers,
    get_portfolio_distribution_by_aging,
    get_branch_risk_percentage,
    get_main_driver_product_in_branch,
    get_top_accounts_by_band,
    get_priority_band_summary,
    categorize_by_aging,
    get_officer_performance,
    get_arrears_time_series,
    get_trend_for_entity,
    get_top_movers,
)
from src.constants import (
    COLORS,
    AGING_BUCKETS,
    PRIORITY_ACTIONS,
    CURRENCY_SYMBOL,
    CHART_CONFIG,
)

# Page configuration
st.set_page_config(
    page_title="Spread Capital - Arrears Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Spread Capital branding
st.markdown("""
<style>
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1E2A5E;
    }
    [data-testid="stSidebar"] {
        background-color: #1E2A5E;
    }
    [data-testid="stSidebar"] .css-1d391kg {
        background-color: #1E2A5E;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #1E2A5E 0%, #2A3A6E 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .kpi-value {
        font-size: 2em;
        font-weight: bold;
        color: #00D1FF;
    }
    
    .kpi-label {
        font-size: 0.9em;
        margin-top: 5px;
        opacity: 0.9;
    }
    
    /* Priority cards */
    .priority-critical {
        border-left: 5px solid #E74C3C;
        background-color: #FFEBEE;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .priority-warning {
        border-left: 5px solid #FF8C00;
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .priority-moderate {
        border-left: 5px solid #FFA500;
        background-color: #FFF8E1;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .priority-early {
        border-left: 5px solid #FFD700;
        background-color: #FFFDE7;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.df = pd.DataFrame()
# Load data from data folder (supports multiple Arrears report files)
@st.cache_data
def load_data():
    """
    Load and cache data from data folder using relative path.
    Automatically finds and loads all files matching 'Arrears report' pattern.
    Supports both .xlsx and .csv files with flexible case-insensitive path checking.
    Uses os.path.join for cross-platform compatibility (Windows/Linux/Cloud).
    """
    # Get project root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try to find data folder (case-insensitive)
    data_folders = [
        os.path.join(root_dir, "data"),
        os.path.join(root_dir, "Data"),
    ]
    
    data_folder = None
    for folder in data_folders:
        if os.path.exists(folder) and os.path.isdir(folder):
            data_folder = folder
            break
    
    if not data_folder:
        st.error("❌ Data folder not found. Expected 'data' or 'Data' folder in project root.")
        st.info(
            "**Solution:** Create a `data` folder in your project root and place your arrears report files there.\n"
            "Expected file naming format: `YYYY.MM.DD [Branch Name] Arrears report.xlsx`"
        )
        return pd.DataFrame()
    
    # Find all files matching "Arrears report" pattern
    try:
        all_files = os.listdir(data_folder)
    except Exception as e:
        st.error(f"❌ Error reading data folder: {str(e)}")
        return pd.DataFrame()
    
    # Filter files: must contain "Arrears report" and be .xlsx or .csv
    matching_files = [
        f for f in all_files
        if ("arrears report" in f.lower()) and (f.lower().endswith('.xlsx') or f.lower().endswith('.csv'))
    ]
    
    if not matching_files:
        st.error(f"❌ No Arrears report files found in {data_folder}")
        st.info(
            f"**Solution:** Place your arrears report files in the `{os.path.basename(data_folder)}` folder.\n"
            "**Expected naming format:** `YYYY.MM.DD [Branch Name] Arrears report.xlsx`\n"
            "**Examples:**\n"
            "  - 2026.02.18 Embu Arrears report.xlsx\n"
            "  - 2026.02.19 Isiolo Arrears report.xlsx"
        )
        return pd.DataFrame()
    
    all_dataframes = []
    
    # Load each file
    for filename in matching_files:
        file_path = os.path.join(data_folder, filename)
        try:
            if filename.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:  # .csv
                df = pd.read_csv(file_path)
            
            if not df.empty:
                all_dataframes.append(df)
                st.success(f"✅ Loaded: {filename} ({len(df)} records)")
            else:
                st.warning(f"⚠️ File {filename} is empty")
        except Exception as e:
            st.warning(f"⚠️ Error loading {filename}: {str(e)}")
            continue
    
    # Combine all dataframes
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        st.success(f"✅ Total: {len(combined_df)} records from {len(all_dataframes)} file(s)")
        return combined_df
    else:
        st.error("❌ No data could be loaded from any files.")
        return pd.DataFrame()


# Helper function to find columns case-insensitively
def get_column_case_insensitive(df: pd.DataFrame, column_name: str):
    """
    Find a column in the dataframe case-insensitively.
    Returns the actual column name if found, None otherwise.
    """
    for col in df.columns:
        if col.lower() == column_name.lower():
            return col
    return None


# Helper function to standardize column names in dataframe
def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a mapping of case-insensitive column names to actual column names.
    This helps the code work with any column name variations.
    """
    if df.empty:
        return df
    
    # Define required columns
    required_columns = ['Branch', 'Loan_Officer', 'Product', 'Arrears', 'Days']
    
    # Check for missing columns and warn user
    missing_cols = []
    for col in required_columns:
        if get_column_case_insensitive(df, col) is None:
            missing_cols.append(col)
    
    if missing_cols:
        st.warning(
            f"⚠️ Missing expected columns: {', '.join(missing_cols)}\n\n"
            f"**Available columns in your data:**\n"
            f"{', '.join(df.columns.tolist())}"
        )
    
    return df


# Main app
def main():
    st.title("📊 Spread Capital - Arrears Analysis System")
    st.markdown("---")
    
    # Load data from data/data.csv
    with st.spinner("Loading data from data/data.csv..."):
        df = load_data()
        st.session_state.df = df
        st.session_state.data_loaded = True
    
    if df.empty:
        st.error("❌ No data loaded. Please check the local data folder.")
        return
    
    # Standardize and validate columns
    df = standardize_column_names(df)
    
    # Sidebar filters
    st.sidebar.title("🔍 Filters")
    # Developer credit next to Filters title
    st.sidebar.markdown(
        "<div style='float:right; color:#e6e6e6; font-size:12px; font-style:italic; margin-top:-26px;'>Developer_Christopher © 2026</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    
    # Timeline -> Calendar: strict single-date filter using Report_Date
    st.sidebar.subheader("Report Date")
    df_filtered = df.copy()
    if 'Report_Date' in df.columns:
        # compute max date from the full dataset (don't mutate original df)
        df_dates = pd.to_datetime(df['Report_Date'], errors='coerce').dt.date
        max_date = df_dates.max()
        selected_date = st.sidebar.date_input("Select Report Date", value=max_date)
        # strict equality filter (one date only)
        df_filtered = df[df_dates == selected_date]
    else:
        # no date column available; keep full df
        df_filtered = df.copy()
    
    # Branch filter with explicit "All" option
    branch_col = get_column_case_insensitive(df_filtered, 'Branch')
    if branch_col:
        branches = sorted(df_filtered[branch_col].dropna().unique())
        branch_options = ["All"] + [str(b) for b in branches]
        selected_branches = st.sidebar.multiselect("Branch", branch_options, default=["All"])
        if selected_branches and "All" not in selected_branches:
            df_filtered = df_filtered[df_filtered[branch_col].isin(selected_branches)]
    else:
        st.warning("⚠️ 'Branch' column not found. Using all data.")
        selected_branches = ["All"]
    
    # Loan Officer filter with explicit "All" option
    officer_col = get_column_case_insensitive(df_filtered, 'Loan_Officer')
    if officer_col:
        officers = sorted(df_filtered[officer_col].dropna().unique())
        officer_options = ["All"] + [str(o) for o in officers]
        selected_officers = st.sidebar.multiselect("Loan Officer", officer_options, default=["All"])
        if selected_officers and "All" not in selected_officers:
            df_filtered = df_filtered[df_filtered[officer_col].isin(selected_officers)]
    else:
        st.warning("⚠️ 'Loan_Officer' column not found. Using all data.")
        selected_officers = ["All"]
    
    # Product filter with explicit "All" option + option to hide Unspecified
    product_col = get_column_case_insensitive(df_filtered, 'Product')
    if product_col:
        products = sorted(df_filtered[product_col].dropna().unique())
        hide_unspecified = False
        if "Unspecified" in products:
            hide_unspecified = st.sidebar.checkbox("Hide Unspecified Products", value=False)
        display_products = [p for p in products if (not hide_unspecified or p != "Unspecified")]
        product_options = ["All"] + [str(p) for p in display_products]
        selected_products = st.sidebar.multiselect("Product", product_options, default=["All"])
        if selected_products and "All" not in selected_products:
            df_filtered = df_filtered[df_filtered[product_col].isin(selected_products)]
        if hide_unspecified:
            df_filtered = df_filtered[df_filtered[product_col] != "Unspecified"]
    else:
        st.warning("⚠️ 'Product' column not found. Using all data.")
        selected_products = ["All"]
    
    # Aging filter with explicit "All" option
    st.sidebar.subheader("Aging Buckets")
    aging_base_options = ["Early Warning (1-30)", "Moderate (31-60)", "Warning (61-90)", "Critical (>90)"]
    aging_options = ["All"] + aging_base_options
    selected_aging = st.sidebar.multiselect("Select Aging Buckets", aging_options, default=["All"])
    
    if selected_aging and "All" not in selected_aging:
        df_categorized = categorize_by_aging(df_filtered)
        df_filtered = df_categorized[df_categorized['Aging_Bucket'].isin(selected_aging)]
    
    # Display filtered record count
    st.sidebar.markdown("---")
    st.sidebar.metric("Records", len(df_filtered))
    
    if df_filtered.empty:
        st.warning("No data matches the selected filters.")
        return
    
    

    # KPI Cards Row (Love Look - 5 high-impact KPIs)
    st.subheader("📈 Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Find columns case-insensitively
    arrears_col = get_column_case_insensitive(df_filtered, 'Arrears')
    principle_col = get_column_case_insensitive(df_filtered, 'Principle')
    totalbalance_col = get_column_case_insensitive(df_filtered, 'TotalBalance')
    days_col = get_column_case_insensitive(df_filtered, 'Days')
    
    # Calculate KPIs with fallbacks
    total_arrears = df_filtered[arrears_col].sum() if arrears_col else 0
    
    if principle_col:
        total_portfolio = df_filtered[principle_col].sum()
    elif totalbalance_col:
        total_portfolio = df_filtered[totalbalance_col].sum()
    else:
        total_portfolio = 0
    
    if days_col:
        accounts_in_arrears = len(df_filtered[df_filtered[days_col].notna() & (df_filtered[days_col] > 0)])
        avg_days = df_filtered[df_filtered[days_col].notna() & (df_filtered[days_col] > 0)][days_col].mean() or 0
    else:
        accounts_in_arrears = 0
        avg_days = 0
    
    par_percentage = calculate_par_percentage(df_filtered)
    
    # 1. Total Arrears
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{CURRENCY_SYMBOL} {total_arrears:,.0f}</div>
            <div class="kpi-label">Total Arrears</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 2. Defaulters (Accounts in Arrears)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{accounts_in_arrears:,}</div>
            <div class="kpi-label">Defaulters (Accounts in Arrears)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 3. Average Days Past Due
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{avg_days:.1f}</div>
            <div class="kpi-label">Average Days Past Due</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 4. PAR %
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{par_percentage:.2f}%</div>
            <div class="kpi-label">PAR %</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 5. Total Principal
    with col5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{CURRENCY_SYMBOL} {total_portfolio:,.0f}</div>
            <div class="kpi-label">Total Principal</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts Section
    st.subheader("📊 Portfolio Analysis Charts")

    
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Arrears by Branch
        if branch_col and arrears_col:
            try:
                branch_totals = df_filtered.groupby(branch_col)[arrears_col].sum().sort_values(ascending=False)
                if not branch_totals.empty:
                    fig_branch = go.Figure(data=[
                        go.Bar(
                            x=branch_totals.index,
                            y=branch_totals.values,
                            marker_color=COLORS['accent_cyan'],
                            text=[f"{CURRENCY_SYMBOL} {val:,.0f}" for val in branch_totals.values],
                            textposition='outside',
                        )
                    ])
                    grand_total = branch_totals.sum()
                    fig_branch.update_layout(
                        title=f"Arrears by Branch<br><sub>Grand Total Arrears: {CURRENCY_SYMBOL} {grand_total:,.0f}</sub>",
                        xaxis_title="Branch",
                        yaxis_title="Arrears Amount",
                        height=400,
                    )
                    st.plotly_chart(fig_branch, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Could not create branch chart: {str(e)}")
        else:
            st.warning("⚠️ Branch or Arrears column not found. Cannot create branch chart.")
    
    with col_chart2:
        # Arrears by Product - Pie chart
        if product_col and arrears_col:
            try:
                product_totals = df_filtered.groupby(product_col)[arrears_col].sum().reset_index()
                if not product_totals.empty:
                    # Highlight JENGA and DUMISHA explicitly, others remain separate
                    fig_product = px.pie(
                        product_totals,
                        values=arrears_col,
                        names=product_col,
                        title="Arrears by Product (JENGA vs DUMISHA vs Others)",
                    )
                    fig_product.update_traces(
                        textposition="inside",
                        textinfo="percent+label+value",
                        hovertemplate="%{label}<br>Arrears: " + CURRENCY_SYMBOL + " %{value:,.0f}<extra></extra>",
                    )
                    st.plotly_chart(fig_product, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Could not create product chart: {str(e)}")
        else:
            st.warning("⚠️ Product or Arrears column not found. Cannot create product chart.")

    
    
    # Arrears by Aging
    st.subheader("Arrears by Aging Buckets")
    df_categorized = categorize_by_aging(df_filtered)
    aging_totals = df_categorized.groupby('Aging_Bucket')['Arrears'].sum()
    
    if not aging_totals.empty:
        # Color mapping for aging buckets
        color_map = {
            'Early Warning (1-30)': COLORS['accent_yellow'],
            'Moderate (31-60)': COLORS['accent_amber'],
            'Warning (61-90)': COLORS['accent_orange'],
            'Critical (>90)': COLORS['accent_red'],
            'Current': '#90EE90'
        }
        colors = [color_map.get(bucket, COLORS['accent_cyan']) for bucket in aging_totals.index]
        
        fig_aging = go.Figure(data=[
            go.Bar(
                x=aging_totals.index,
                y=aging_totals.values,
                marker_color=colors,
                text=[f"{CURRENCY_SYMBOL} {val:,.0f}" for val in aging_totals.values],
                textposition='outside',
            )
        ])
        grand_total = aging_totals.sum()
        fig_aging.update_layout(
            title=f"Arrears by Aging Buckets<br><sub>Grand Total Arrears: {CURRENCY_SYMBOL} {grand_total:,.0f}</sub>",
            xaxis_title="Aging Bucket",
            yaxis_title="Arrears Amount",
            height=400,
        )
        st.plotly_chart(fig_aging, use_container_width=True)
    
    st.markdown("---")
    
    # Strategic Portfolio Recommendations
    st.subheader("📊 Strategic Portfolio Recommendations")
    
    priority_summary = get_priority_band_summary(df_filtered)
    
    for _, row in priority_summary.iterrows():
        priority = row['Priority']
        aging_bucket = row['Aging_Bucket']
        count = int(row['Account_Count'])
        total_arrears = row['Total_Arrears']
        action = PRIORITY_ACTIONS.get(priority, "Review Required")
        
        if priority == "Current" or count == 0:
            continue
        
        # Get top accounts for this band
        top_accounts = get_top_accounts_by_band(df_filtered, priority, top_n=5)
        
        # Determine emoji
        emoji_map = {
            "Critical": "🔴",
            "Warning": "🟠",
            "Moderate": "🟡",
            "Early Warning": "🟡"
        }
        emoji = emoji_map.get(priority, "📋")
        
        with st.expander(f"{emoji} {priority} Priority ({aging_bucket}) - {count} Accounts, {CURRENCY_SYMBOL} {total_arrears:,.0f}"):
            st.markdown(f"**Recommended Action:** {action}")
            st.markdown(f"**Total Accounts:** {count}")
            st.markdown(f"**Total Arrears:** {CURRENCY_SYMBOL} {total_arrears:,.0f}")
            
            if not top_accounts.empty:
                st.markdown("**Top 5 Accounts by Arrears:**")
                display_df = top_accounts.copy()
                display_df['Arrears'] = display_df['Arrears'].apply(lambda x: f"{CURRENCY_SYMBOL} {x:,.2f}")
                display_df['Principle'] = display_df['Principle'].apply(lambda x: f"{CURRENCY_SYMBOL} {x:,.2f}" if pd.notna(x) else "N/A")
                st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Action-level worklist: exactly which account needs what action
    st.markdown("---")
    st.subheader("🧾 Action-Level Worklist")
    worklist_df = categorize_by_aging(df_filtered)
    
    def map_action(bucket: str) -> str:
        if bucket == "Early Warning (1-30)":
            return "Call Back / SMS Reminder"
        if bucket in ["Moderate (31-60)", "Warning (61-90)"]:
            return "Physical Visit / Site Visit & Guarantor Engagement"
        if bucket == "Critical (>90)":
            return "Escalate Recovery Measures / Legal Follow-up"
        return "Monitor"
    
    worklist_df['Recommended_Action'] = worklist_df['Aging_Bucket'].apply(map_action)
    
    # Compact view focused on frontline execution
    cols_to_show = ['AccountID', 'Branch', 'Loan_Officer', 'Product', 'Days', 'Arrears', 'Aging_Bucket', 'Recommended_Action']
    cols_to_show = [c for c in cols_to_show if c in worklist_df.columns]
    
    # Separate tabs for different action types
    tab_call, tab_visit, tab_recovery = st.tabs(["Call Backs (1–30 days)", "Physical Visits (31–90 days)", "Recovery Escalations (>90 days)"])
    
    def render_worklist_tab(df_tab, label_prefix: str):
        """Render table + CSV/Excel export buttons for a given worklist slice."""
        if df_tab.empty:
            st.caption(f"No accounts currently in {label_prefix.lower()}.")
            return
        view = df_tab[cols_to_show].copy()
        st.dataframe(view, use_container_width=True)

        # CSV export
        csv_bytes = view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label=f"⬇️ Download {label_prefix} List (CSV)",
            data=csv_bytes,
            file_name=f"{label_prefix.replace(' ', '_').lower()}_worklist.csv",
            mime="text/csv",
        )

        # Excel export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            view.to_excel(writer, index=False, sheet_name="Worklist")
        buffer.seek(0)
        st.download_button(
            label=f"⬇️ Download {label_prefix} List (Excel)",
            data=buffer,
            file_name=f"{label_prefix.replace(' ', '_').lower()}_worklist.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with tab_call:
        call_df = worklist_df[worklist_df['Recommended_Action'].str.contains("Call Back")]
        render_worklist_tab(call_df, "Call Back")
    
    with tab_visit:
        visit_df = worklist_df[worklist_df['Recommended_Action'].str.contains("Physical Visit")]
        render_worklist_tab(visit_df, "Physical Visit")
    
    with tab_recovery:
        recovery_df = worklist_df[worklist_df['Recommended_Action'].str.contains("Recovery Measures")]
        render_worklist_tab(recovery_df, "Recovery Escalation")
    
    st.markdown("---")
    
    # Performance Rankings & Insights
    st.subheader("🎯 Performance Rankings & Insights")
    
    col_rank1, col_rank2 = st.columns(2)
    
    with col_rank1:
        st.markdown("### Top Risk Branch")
        top_branch = get_top_risk_branch(df_filtered)
        if top_branch:
            branch_name, branch_amount = top_branch
            st.metric("Branch", branch_name.title(), f"{CURRENCY_SYMBOL} {branch_amount:,.0f}")
        
        st.markdown("### Top Risk Product")
        top_product = get_top_risk_product(df_filtered)
        if top_product:
            product_name, product_ratio = top_product
            st.metric("Product", product_name, f"Ratio: {product_ratio:.2%}")
    
    with col_rank2:
        st.markdown("### Officer Performance – Praise vs Improve")
        officer_perf = get_officer_performance(df_filtered)
        if not officer_perf.empty:
            # Best 5 (praise) and worst 5 (needs improvement)
            best = officer_perf.nsmallest(5, 'Ratio')
            worst = officer_perf.nlargest(5, 'Ratio')
            
            tab_best, tab_worst = st.tabs(["👏 Officers to Praise", "⚠️ Officers Needing Improvement"])
            
            with tab_best:
                st.dataframe(
                    best[['Officer', 'Arrears', 'Principle', 'Ratio']].rename(columns={
                        'Ratio': 'Arrears/Portfolio Ratio'
                    }),
                    use_container_width=True,
                )
            
            with tab_worst:
                st.dataframe(
                    worst[['Officer', 'Arrears', 'Principle', 'Ratio']].rename(columns={
                        'Ratio': 'Arrears/Portfolio Ratio'
                    }),
                    use_container_width=True,
                )
    
    # Dynamic Branch Insights
    if selected_branches and len(selected_branches) == 1:
        branch = selected_branches[0]
        risk_pct = get_branch_risk_percentage(df, branch)
        main_product = get_main_driver_product_in_branch(df_filtered, branch)
        
        st.markdown("### Branch-Specific Insights")
        st.info(f"**Branch {branch.title()}** currently holds **{risk_pct:.2f}%** of total portfolio risk.")
        if main_product:
            st.info(f"**Recommendation:** Immediate focus on **{main_product}**, which is the main driver of arrears in this branch.")
    
    # Portfolio Distribution by Aging
    st.markdown("---")
    st.subheader("📈 Portfolio Distribution by Aging Buckets")
    portfolio_dist = get_portfolio_distribution_by_aging(df_filtered)
    if not portfolio_dist.empty:
        st.dataframe(portfolio_dist, use_container_width=True)
        
        # Visual representation
        fig_pie = px.pie(
            portfolio_dist,
            values='Total_Arrears',
            names='Aging_Bucket',
            title="Arrears Distribution by Aging Buckets",
            color='Aging_Bucket',
            color_discrete_map={
                'Early Warning (1-30)': COLORS['accent_yellow'],
                'Moderate (31-60)': COLORS['accent_amber'],
                'Warning (61-90)': COLORS['accent_orange'],
                'Critical (>90)': COLORS['accent_red'],
                'Current': '#90EE90'
            }
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label+value')
        st.plotly_chart(fig_pie, use_container_width=True)

        # Trend Movement Analysis expander (moved here: uses historical data but respects Branch/Officer selections)
        with st.expander("📈 View Arrears Trend Movement", expanded=False):
            # Build df_trend from full dataset but apply selected Branch/Officer filters
            df_trend = df.copy()
            # apply branch filter selections from sidebar if present
            try:
                if selected_branches and "All" not in selected_branches:
                    df_trend = df_trend[df_trend['Branch'].isin(selected_branches)]
            except NameError:
                pass
            try:
                if selected_officers and "All" not in selected_officers:
                    df_trend = df_trend[df_trend['Loan_Officer'].isin(selected_officers)]
            except NameError:
                pass

            # Radio to choose comparison entity
            compare_choice = st.radio("Compare Trend By:", ["Branch", "Loan Officer"])
            grp_col = 'Branch' if compare_choice == 'Branch' else 'Loan_Officer'

            if 'Report_Date' in df_trend.columns:
                df_trend = df_trend.copy()
                df_trend['Report_Date'] = pd.to_datetime(df_trend['Report_Date'], errors='coerce')
                df_trend = df_trend.dropna(subset=['Report_Date'])

                trend_df = df_trend.groupby([pd.Grouper(key='Report_Date', freq='D'), grp_col])['Arrears'].sum().reset_index()
                if not trend_df.empty:
                    try:
                        colors_list = [COLORS['accent_cyan'], COLORS['accent_orange'], COLORS['accent_amber'], COLORS['accent_red'], COLORS['accent_yellow']]
                        fig_trend = px.line(trend_df, x='Report_Date', y='Arrears', color=grp_col, markers=True, color_discrete_sequence=colors_list)
                        fig_trend.update_layout(
                            title="Arrears Movement Over Time",
                            template='plotly_dark',
                            height=360,
                            legend_title=grp_col,
                        )
                        st.plotly_chart(fig_trend, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error plotting trend movement: {e}")
                else:
                    st.info("No historical data available for the selected Branch/Officer filters.")
            else:
                st.info("No `Report_Date` column available in dataset to show trends.")

    # --- Daily Arrears Movement (moved to bottom of page) ---
    st.markdown("---")
    st.subheader("📈 Daily Arrears Movement")
    group_choice = st.radio("Group Movement By:", ["Branch", "Loan_Officer", "Product"], horizontal=True)

    # Build trend dataframe from full df (ignore selected_date) but apply other sidebar filters
    df_trend = df.copy()
    # apply branch filter selections
    try:
        if selected_branches and "All" not in selected_branches:
            df_trend = df_trend[df_trend['Branch'].isin(selected_branches)]
    except NameError:
        pass
    # apply officer filter selections
    try:
        if selected_officers and "All" not in selected_officers:
            df_trend = df_trend[df_trend['Loan_Officer'].isin(selected_officers)]
    except NameError:
        pass
    # apply product filter selections
    try:
        if selected_products and "All" not in selected_products:
            df_trend = df_trend[df_trend['Product'].isin(selected_products)]
    except NameError:
        pass

    if 'Report_Date' in df_trend.columns:
        df_trend = df_trend.copy()
        df_trend['Report_Date'] = pd.to_datetime(df_trend['Report_Date'], errors='coerce')
        df_trend = df_trend.dropna(subset=['Report_Date'])

        grp_col = group_choice
        trend_grp = df_trend.groupby([pd.Grouper(key='Report_Date', freq='D'), grp_col])['Arrears'].sum().reset_index()

        # If 'All' selected and too many entities, limit to top 10 by total arrears
        try:
            selected_list = selected_branches if grp_col == 'Branch' else (selected_officers if grp_col == 'Loan_Officer' else selected_products)
        except NameError:
            selected_list = None

        if selected_list is not None and "All" in selected_list:
            # compute top entities by total arrears
            totals = df_trend.groupby(grp_col)['Arrears'].sum().nlargest(10)
            top_entities = totals.index.tolist()
            if trend_grp[grp_col].nunique() > 10:
                trend_grp = trend_grp[trend_grp[grp_col].isin(top_entities)]

        if not trend_grp.empty:
            try:
                palette = [COLORS['accent_cyan'], COLORS['accent_orange'], COLORS['accent_amber'], COLORS['accent_red'], COLORS['accent_yellow']]
                fig_daily = px.line(
                    trend_grp,
                    x='Report_Date',
                    y='Arrears',
                    color=grp_col,
                    markers=True,
                    color_discrete_sequence=palette,
                )
                fig_daily.update_traces(hovertemplate=f"%{{x}}<br>Arrears: {CURRENCY_SYMBOL} %{{y:,.0f}}<extra></extra>")
                fig_daily.update_layout(height=450, template='plotly_dark', title='Arrears Movement Over Time')
                st.plotly_chart(fig_daily, use_container_width=True)
            except Exception as e:
                st.error(f"Error plotting daily arrears movement: {e}")
        else:
            st.info("No historical data available for the selected filters to plot daily movement.")
    else:
        st.info("No `Report_Date` column in dataset; cannot plot daily movement.")
    
    # ============================================================================
    # Data Source Management Section (at bottom of page)
    # ============================================================================
    st.markdown("---")
    st.subheader("📁 Data Source")
    
    st.info(
        "**Data is automatically loaded from** `data/data.csv` in the project root directory. "
        "This ensures compatibility with GitHub and Streamlit Cloud deployments."
    )
    

if __name__ == "__main__":
    main()
