"""
Constants and configuration for Spread Capital Arrears Analysis System
"""

import os

# Data Paths - Use relative path for GitHub/Streamlit Cloud compatibility
# Get root directory (parent of src/) and join with data folder
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(_root_dir, "data")

# Spread Capital Brand Colors
COLORS = {
    "sidebar_bg": "#1E2A5E",  # Navy Blue
    "accent_cyan": "#00D1FF",  # Cyan for success/low risk
    "accent_red": "#E74C3C",   # Red for high-risk alerts
    "accent_orange": "#FF8C00",  # Orange for warnings
    "accent_amber": "#FFA500",   # Amber/Light Orange for moderate
    "accent_yellow": "#FFD700",  # Yellow for early warning
    "text_light": "#FFFFFF",
    "text_dark": "#000000",
}

# Aging Buckets (Days Past Due)
AGING_BUCKETS = {
    "Early Warning": (1, 30),
    "Moderate": (31, 60),
    "Warning": (61, 90),
    "Critical": (91, None),  # > 90
}

# Column Mapping - Flexible detection patterns
COLUMN_PATTERNS = {
    "arrears": ["arrears", "arrear", "overdue", "outstanding", "balance due"],
    "principle": ["principle", "principal", "loan amount", "disbursed", "disbursement"],
    "total_balance": ["total balance", "totalbalance", "outstanding balance", "loan balance"],
    "days": ["days", "overdue days", "past due", "days overdue", "aging"],
    "product": ["product", "loan type", "loan product", "product type"],
    "account_id": ["memberno", "member no", "account", "account id", "accountid", "client id"],
    "member_name": ["membername", "member name", "client name", "customer name", "borrower name"],
    "branch": ["branch"],
    "loan_officer": ["loan officer", "officer", "lo"],
}

# Default column positions (fallback if header detection fails)
DEFAULT_COLUMNS = {
    "arrears": 15,  # Column P (0-indexed: 15)
    "principle": None,  # Will be detected or calculated
    "total_balance": None,
    "days": None,
    "product": None,
    "account_id": 0,  # Usually column A
    "member_name": None,
}

# Header keywords for Branch/Loan Officer extraction
HEADER_KEYWORDS = {
    "branch": ["branch :", "branch:", "branch"],
    "loan_officer": ["loan officer :", "loan officer:", "loan officer"],
}

# Priority Actions
PRIORITY_ACTIONS = {
    "Critical": "Immediate Legal Demand / Asset Recovery",
    "Warning": "Guarantor Notification & Site Visit",
    "Moderate": "Escalated Follow-up & Payment Plan Review",
    "Early Warning": "SMS / Phone Call reminders",
}

# Currency
CURRENCY = "KES"
CURRENCY_SYMBOL = "KES"

# Chart Configuration
CHART_CONFIG = {
    "bar_color": COLORS["accent_cyan"],
    "critical_color": COLORS["accent_red"],
    "warning_color": COLORS["accent_orange"],
    "moderate_color": COLORS["accent_amber"],
    "early_warning_color": COLORS["accent_yellow"],
}