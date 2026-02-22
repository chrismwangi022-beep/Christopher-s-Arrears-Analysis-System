"""
Spread Capital Arrears Analysis System
Main Streamlit Application
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import io
import git

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import load_all_data
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
    DATA_FOLDER,
    ADMIN_PASSWORD,
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
    [data-testid="stSidebar"] {
        background-color: #1E2A5E;
    }
    
    /* Sidebar Headers and Labels - White & Calibri */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] strong {
        color: #FFFFFF !important;
        font-family: 'Calibri', sans-serif !important;
    }
    
    /* Sidebar Toggle Icon (Expanded - Left Arrow) -> White */
    [data-testid="stSidebarCollapseButton"] svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    
    /* Sidebar Toggle Icon (Collapsed - Right Arrow) -> Black */
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: #000000 !important;
        color: #000000 !important;
    }
    
    /* Fix File Uploader Background & Text in Sidebar */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background-color: #1E2A5E !important;
        border: 1px dashed #FFFFFF !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background-color: #2A3A6E !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    
    /* Fix Uploaded File Info (Filename, Size) & Icons in Sidebar */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] span, /* Covers prompt text and file names */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small { /* Covers file size limit text */
        color: #FFFFFF !important;
        font-family: 'Calibri', sans-serif !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] svg {
        fill: #FFFFFF !important;
    }
    
    /* Fix Standard Buttons in Sidebar (e.g. Save button) */
    [data-testid="stSidebar"] .stButton button {
        background-color: #2A3A6E !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    
    /* Fix Alerts (Warning, Success, Error) in Sidebar */
    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background-color: #2A3A6E !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
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

# Load data
@st.cache_data
def load_data():
    """Load and cache data."""
    return load_all_data()

# Main app
def main():
    st.title("📊 Spread Capital - Arrears Analysis System")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
        st.session_state.df = df
        st.session_state.data_loaded = True
    
    if df.empty:
        st.error("No data loaded. Please check the data folder path.")
        return
    
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
    branches = sorted(df_filtered['Branch'].dropna().unique())
    branch_options = ["All"] + branches
    selected_branches = st.sidebar.multiselect("Branch", branch_options, default=["All"])
    if selected_branches and "All" not in selected_branches:
        df_filtered = df_filtered[df_filtered['Branch'].isin(selected_branches)]
    
    # Loan Officer filter with explicit "All" option
    officers = sorted(df_filtered['Loan_Officer'].dropna().unique())
    officer_options = ["All"] + officers
    selected_officers = st.sidebar.multiselect("Loan Officer", officer_options, default=["All"])
    if selected_officers and "All" not in selected_officers:
        df_filtered = df_filtered[df_filtered['Loan_Officer'].isin(selected_officers)]
    
    # Product filter with explicit "All" option + option to hide Unspecified
    products = sorted(df_filtered['Product'].dropna().unique())
    hide_unspecified = False
    if "Unspecified" in products:
        hide_unspecified = st.sidebar.checkbox("Hide Unspecified Products", value=False)
    display_products = [p for p in products if (not hide_unspecified or p != "Unspecified")]
    product_options = ["All"] + display_products
    selected_products = st.sidebar.multiselect("Product", product_options, default=["All"])
    if selected_products and "All" not in selected_products:
        df_filtered = df_filtered[df_filtered['Product'].isin(selected_products)]
    if hide_unspecified:
        df_filtered = df_filtered[df_filtered['Product'] != "Unspecified"]
    
    # Aging filter with explicit "All" option
    st.sidebar.subheader("Aging Buckets")
    aging_base_options = ["Early Warning (1-30)", "Moderate (31-60)", "Warning (61-90)", "Critical (>90)"]
    aging_options = ["All"] + aging_base_options
    selected_aging = st.sidebar.multiselect("Select Aging Buckets", aging_options, default=["All"])
    
    # --- REFACTOR: Categorize once, then filter if needed. This df is used for all displays. ---
    df_categorized = categorize_by_aging(df_filtered)
    
    if selected_aging and "All" not in selected_aging:
        df_display = df_categorized[df_categorized['Aging_Bucket'].isin(selected_aging)]
    else:
        df_display = df_categorized
    
    # Display filtered record count
    st.sidebar.markdown("---")
    st.sidebar.metric("Records", len(df_display))
    
    st.sidebar.markdown("---")
    st.sidebar.title("Data Management")
    
    # Display success message if file was saved in previous run
    if 'upload_success' in st.session_state:
        st.sidebar.success(st.session_state.upload_success)
        del st.session_state['upload_success']
    
    password_input = st.sidebar.text_input("Enter Admin Password", type="password")
    
    if password_input == ADMIN_PASSWORD:
        uploaded_files = st.sidebar.file_uploader(
            "Upload & Save Daily Reports",
            type=['csv', 'xlsx'],
            accept_multiple_files=True,
            help="Upload new reports to permanently save them to the system's data folder."
        )

        if uploaded_files:
            # Check for existing files
            existing_files = [f.name for f in uploaded_files if os.path.exists(os.path.join(DATA_FOLDER, f.name))]
            overwrite = False
            
            st.sidebar.write(f"**Selected:** {len(uploaded_files)} files")

            if existing_files:
                st.sidebar.warning(f"⚠️ {len(existing_files)} file(s) already exist.")
                overwrite = st.sidebar.checkbox("Overwrite existing files?")

            if st.sidebar.button("💾 Save Files to System"):
                # Ensure data folder exists
                if not os.path.exists(DATA_FOLDER):
                    os.makedirs(DATA_FOLDER)

                saved_count = 0
                skipped_count = 0
                errors = []
                saved_file_paths = []
                
                for uploaded_file in uploaded_files:
                    destination_path = os.path.join(DATA_FOLDER, uploaded_file.name)
                    
                    if os.path.exists(destination_path) and not overwrite:
                        skipped_count += 1
                        continue

                    try:
                        with open(destination_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        saved_count += 1
                        saved_file_paths.append(destination_path)
                    except Exception as e:
                        errors.append(f"{uploaded_file.name}: {e}")
                
                if saved_count > 0:
                    # --- GIT PUSH LOGIC ---
                    git_success_message = None
                    git_error_message = None
                    try:
                        github_token = st.secrets.get("GITHUB_TOKEN")
                        if not github_token:
                            git_error_message = "🚫 GitHub token not found in st.secrets. Cannot push updates."
                        else:
                            repo_path = os.path.dirname(os.path.abspath(__file__))
                            repo = git.Repo(repo_path)
                            
                            repo.index.add(saved_file_paths)
                            
                            if repo.is_dirty(working_tree=False): # Check for staged changes
                                repo.index.commit("Daily Data Update")
                                origin = repo.remote(name='origin')
                                repo_url = origin.url
                                
                                if repo_url.startswith("https://"):
                                    authed_url = repo_url.replace("https://", f"https://{github_token}@")
                                    repo.git.push(authed_url, repo.active_branch.name)
                                    git_success_message = "✅ Data pushed to GitHub successfully!"
                                else:
                                    git_error_message = "Git push only supported for HTTPS remotes."
                            else:
                                git_success_message = "No new file changes to push to GitHub."
                    except Exception as e:
                        git_error_message = f"🔥 Failed to push to GitHub: {e}"

                    # Combine messages and rerun
                    local_save_msg = f"✅ Saved {saved_count} files locally."
                    git_msg = git_success_message or git_error_message
                    final_msg = f"{local_save_msg} | {git_msg}" if git_msg else local_save_msg
                    st.session_state.upload_success = final_msg
                    st.toast("Reloading all data...")
                    st.cache_data.clear()
                    st.rerun()
                
                elif skipped_count > 0:
                    st.sidebar.warning(f"Skipped {skipped_count} files (Overwrite not selected).")
                
                if errors:
                    for err in errors:
                        st.sidebar.error(err)
    elif password_input:
        st.sidebar.error("Incorrect Password")

    if df_display.empty:
        st.warning("No data matches the selected filters.")
        return
    
    # KPI Cards Row (Love Look - 5 high-impact KPIs)
    st.subheader("📈 Key Performance Indicators")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_arrears = df_display['Arrears'].sum()
    total_portfolio = df_display['Principle'].sum() if 'Principle' in df_display.columns else df_display['TotalBalance'].sum()
    accounts_in_arrears = len(df_display[df_display['Days'].notna() & (df_display['Days'] > 0)])
    avg_days = df_display[df_display['Days'].notna() & (df_display['Days'] > 0)]['Days'].mean() or 0
    par_percentage = calculate_par_percentage(df_display)
    
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
        branch_totals = df_display.groupby('Branch')['Arrears'].sum().sort_values(ascending=False)
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
                dragmode='pan',
            )
            st.plotly_chart(fig_branch, use_container_width=True, config={'scrollZoom': False})
    
    with col_chart2:
        # Arrears by Product - Pie chart (JENGA vs DUMISHA vs others)
        product_totals = df_display.groupby('Product')['Arrears'].sum().reset_index()
        if not product_totals.empty:
            # Highlight JENGA and DUMISHA explicitly, others remain separate
            fig_product = px.pie(
                product_totals,
                values="Arrears",
                names="Product",
                title="Arrears by Product (JENGA vs DUMISHA vs Others)",
            )
            fig_product.update_traces(
                textposition="inside",
                textinfo="percent+label+value",
                hovertemplate="%{label}<br>Arrears: " + CURRENCY_SYMBOL + " %{value:,.0f}<extra></extra>",
            )
            fig_product.update_layout(dragmode='pan')
            st.plotly_chart(fig_product, use_container_width=True, config={'scrollZoom': False})

    
    
    # Arrears by Aging
    st.subheader("Arrears by Aging Buckets")
    aging_totals = df_display.groupby('Aging_Bucket')['Arrears'].sum()
    
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
            dragmode='pan',
        )
        st.plotly_chart(fig_aging, use_container_width=True, config={'scrollZoom': False})
    
    st.markdown("---")
    
    # Strategic Portfolio Recommendations
    st.subheader("📊 Strategic Portfolio Recommendations")
    
    priority_summary = get_priority_band_summary(df_display)
    
    for _, row in priority_summary.iterrows():
        priority = row['Priority']
        aging_bucket = row['Aging_Bucket']
        count = int(row['Account_Count'])
        total_arrears = row['Total_Arrears']
        action = PRIORITY_ACTIONS.get(priority, "Review Required")
        
        if priority == "Current" or count == 0:
            continue
        
        # Get top accounts for this band
        top_accounts = get_top_accounts_by_band(df_display, priority, top_n=5)
        
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
    worklist_df = df_display.copy() # Use the already categorized display dataframe
    
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

        # --- REFACTOR: Place download buttons side-by-side ---
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            # CSV export
            csv_bytes = view.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=f"⬇️ Download {label_prefix} List (CSV)",
                data=csv_bytes,
                file_name=f"{label_prefix.replace(' ', '_').lower()}_worklist.csv",
                mime="text/csv",
            )
        with dl_col2:
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
        top_branch = get_top_risk_branch(df_display)
        if top_branch:
            branch_name, branch_amount = top_branch
            st.metric("Branch", branch_name.title(), f"{CURRENCY_SYMBOL} {branch_amount:,.0f}")
        
        st.markdown("### Top Risk Product")
        top_product = get_top_risk_product(df_display)
        if top_product:
            product_name, product_ratio = top_product
            st.metric("Product", product_name, f"Ratio: {product_ratio:.2%}")
    
    with col_rank2:
        st.markdown("### Officer Performance – Praise vs Improve")
        officer_perf = get_officer_performance(df_display)
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
        main_product = get_main_driver_product_in_branch(df_display, branch)
        
        st.markdown("### Branch-Specific Insights")
        st.info(f"**Branch {branch.title()}** currently holds **{risk_pct:.2f}%** of total portfolio risk.")
        if main_product:
            st.info(f"**Recommendation:** Immediate focus on **{main_product}**, which is the main driver of arrears in this branch.")
    
    # Portfolio Distribution by Aging
    st.markdown("---")
    st.subheader("📈 Portfolio Distribution by Aging Buckets")
    portfolio_dist = get_portfolio_distribution_by_aging(df_display)
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
        fig_pie.update_layout(dragmode='pan')
        st.plotly_chart(fig_pie, use_container_width=True, config={'scrollZoom': False})

    # --- REFACTOR: Consolidated Trend Analysis Section ---
    st.markdown("---")
    st.subheader("📈 Trend Analysis")
    group_choice = st.radio("Group Trends By:", ["Branch", "Loan_Officer", "Product"], horizontal=True, key="trend_group")

    # Build trend dataframe from the full dataset (df), but apply the entity filters from the sidebar.
    # This ignores the date filter to show historical trends for the selected entities.
    df_trend = df.copy()
    if selected_branches and "All" not in selected_branches:
        df_trend = df_trend[df_trend['Branch'].isin(selected_branches)]
    if selected_officers and "All" not in selected_officers:
        df_trend = df_trend[df_trend['Loan_Officer'].isin(selected_officers)]
    if selected_products and "All" not in selected_products:
        df_trend = df_trend[df_trend['Product'].isin(selected_products)]

    if 'Report_Date' in df_trend.columns:
        df_trend = df_trend.copy()
        df_trend['Report_Date'] = pd.to_datetime(df_trend['Report_Date'], errors='coerce')
        df_trend = df_trend.dropna(subset=['Report_Date'])

        trend_grp = df_trend.groupby([pd.Grouper(key='Report_Date', freq='D'), group_choice])['Arrears'].sum().reset_index()

        # If 'All' selected and too many entities, limit to top 10 by total arrears
        selected_list_map = {"Branch": selected_branches, "Loan_Officer": selected_officers, "Product": selected_products}
        selected_list = selected_list_map.get(group_choice)

        if selected_list is not None and "All" in selected_list:
            # compute top entities by total arrears
            totals = df_trend.groupby(group_choice)['Arrears'].sum().nlargest(10)
            top_entities = totals.index.tolist()
            if trend_grp[group_choice].nunique() > 10:
                trend_grp = trend_grp[trend_grp[group_choice].isin(top_entities)]

        if not trend_grp.empty:
            try:
                palette = [COLORS['accent_cyan'], COLORS['accent_orange'], COLORS['accent_amber'], COLORS['accent_red'], COLORS['accent_yellow']]
                fig_daily = px.line(
                    trend_grp,
                    x='Report_Date',
                    y='Arrears',
                    color=group_choice,
                    markers=True,
                    color_discrete_sequence=palette,
                )
                fig_daily.update_traces(hovertemplate=f"%{{x}}<br>Arrears: {CURRENCY_SYMBOL} %{{y:,.0f}}<extra></extra>")
                fig_daily.update_layout(height=450, template='plotly_dark', title=f'Arrears Movement Over Time by {group_choice}', dragmode='pan')
                st.plotly_chart(fig_daily, use_container_width=True, config={'scrollZoom': False})
            except Exception as e:
                st.error(f"Error plotting trend analysis: {e}")
        else:
            st.info("No historical data available for the selected filters to plot trends.")
    else:
        st.info("No `Report_Date` column in dataset; cannot plot trends.")
    

if __name__ == "__main__":
    main()