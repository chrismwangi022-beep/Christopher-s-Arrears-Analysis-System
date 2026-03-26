# Christopher-s-Arrears-Analysis-System
Christopher's Arrears Analysis System is a high-performance, cloud-integrated financial analytics web application built with Streamlit. This system transforms raw portfolio data into actionable recovery insights providIing portfolio managers with real-time visibility into arrears movement, risk distribution, and loan officer performance.
=======
# Spread Capital - Arrears Analysis System

A comprehensive Streamlit-based dashboard for analyzing loan arrears and portfolio risk with high-level Portfolio Intelligence.

## Features

### 📊 Key Performance Indicators (KPIs)
- **Total Arrears**: Sum of all outstanding arrears
- **Defaulters**: Count of accounts in arrears (Days > 0)
- **Average Days Past Due**: Mean days in arrears across defaulted accounts
- **PAR %**: Portfolio at Risk percentage
- **Total Principal**: Total portfolio value (Principle)

### 📈 Interactive Charts
- **Arrears by Branch**: Bar chart with total labels on bars and Grand Total annotation
- **Arrears by Product**: Pie chart with JENGA vs DUMISHA vs other products, showing value and percentage
- **Arrears by Aging Buckets**: Color-coded bar chart for 0-30, 31-60, 61-90, and 90+ days (Current, Early Warning, Moderate, Warning, Critical)
- **Portfolio Distribution**: Pie chart showing arrears distribution across aging buckets

### 🔍 Advanced Filtering (Slicers)
- **Timeline**: Today, Last Week, Last Month, Last Quarter, All Time
- **Branch**: Multi-select filter
- **Loan Officer**: Multi-select filter
- **Product**: Multi-select filter
- **Aging Buckets**: Multi-select (1-30, 31-60, 61-90, 90+)

### 📊 Strategic Portfolio Recommendations
AI-powered recommendations organized by priority bands:

| Priority | Days Past Due | Action |
|----------|---------------|--------|
| **Critical** | > 90 | Immediate Legal Demand / Asset Recovery |
| **Warning** | 61-90 | Guarantor Notification & Site Visit |
| **Moderate** | 31-60 | Escalated Follow-up & Payment Plan Review |
| **Early Warning** | 1-30 | SMS / Phone Call reminders |

Each priority band shows:
- Total account count
- Total arrears amount
- Top 5 accounts by arrears amount

### 🎯 Performance Rankings & Insights
- **Top Risk Branch**: Branch with highest total arrears
- **Top Risk Product**: Product with highest arrears-to-portfolio ratio
- **Star Performers**: Top 5 officers with lowest arrears-to-portfolio ratio
- **Branch-Specific Insights**: Dynamic recommendations when a single branch is selected

### 📈 Portfolio Distribution Analysis
- Breakdown by aging buckets (1-30, 31-60, 61-90, 90+)
- Account count per bucket
- Total arrears per bucket
- Portfolio percentage per bucket

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd "Christopher's Arrears Analysis System"
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Data Source Path
The system reads data from:
```
C:\Users\ADMIN\Desktop\Christopher\Arrears Reports\Arears Reports formating folder\Documents
```

To change this path, edit `src/constants.py`:
```python
DATA_FOLDER = r"your\path\to\data\folder"
```

### Data Format
The system expects CSV or Excel files with:
- **Branch** information in row headers (e.g., "Branch : [Name]")
- **Loan Officer** information in row headers (e.g., "Loan Officer : [Name]")
- **Arrears** amount in column P (16th column, 0-indexed: 15)
- Optional columns: Principle, TotalBalance, Days, Product, AccountID

The system automatically:
- Extracts Branch and Loan Officer from row headers
- Forward-fills Branch and Loan Officer values
- Detects columns by header patterns
- Handles missing columns gracefully

## Usage

1. **Ensure data files are in the Documents folder**

2. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

3. **Access the dashboard:**
   - The app will open in your default browser
   - Default URL: `http://localhost:8501`

4. **Use the sidebar filters:**
   - Select timeline period
   - Filter by Branch, Loan Officer, Product
   - Select specific Aging Buckets
   - All charts and metrics update automatically

## Spread Capital Branding

The dashboard features Spread Capital branding:
- **Sidebar**: Navy Blue (#1E2A5E)
- **Accent Colors**:
  - Cyan (#00D1FF) for success metrics
  - Red (#E74C3C) for critical alerts
  - Orange (#FF8C00) for warnings
  - Amber (#FFA500) for moderate risk
  - Yellow (#FFD700) for early warnings

## Architecture

```
Christopher's Arrears Analysis System/
├── src/
│   ├── __init__.py
│   ├── constants.py          # Configuration, colors, column mappings
│   ├── data_loader.py        # CSV/Excel loading, Branch/Officer extraction
│   └── calculations.py      # PAR, ratios, risk rankings
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Key Functions

### Data Loading (`src/data_loader.py`)
- `load_all_data()`: Loads all CSV/Excel files from Documents folder
- `extract_branch_and_officer()`: Extracts and forward-fills Branch/Loan Officer
- `detect_column_by_pattern()`: Flexible column detection

### Calculations (`src/calculations.py`)
- `calculate_par_percentage()`: Calculates Portfolio at Risk %
- `get_top_risk_branch()`: Identifies highest risk branch
- `get_top_risk_product()`: Identifies highest risk product
- `get_star_performers()`: Top performing officers
- `get_portfolio_distribution_by_aging()`: Aging bucket analysis

## Troubleshooting

### No data loaded
- Check that the `DATA_FOLDER` path in `src/constants.py` is correct
- Ensure CSV/Excel files exist in the Documents folder
- Verify files are not named "Movement Report" (these are excluded)

### Missing columns / Unknown product
- The system handles missing Principle, TotalBalance, Days, and Product columns
- Missing Principle defaults to Arrears value
- Missing TotalBalance defaults to Principle + Arrears
- Missing Days will exclude accounts from aging-based analysis
- Missing Product is explicitly tagged as **\"Unspecified\"** so you can see how many records need data cleanup. You can hide these in the Product filter via the **\"Hide Unspecified Products\"** checkbox.

### Branch/Officer not detected
- Ensure row headers contain "Branch :" or "Loan Officer :" keywords
- Check that values are in the adjacent column (A or B)
- Branch fallback: extracted from filename (first word)

## License

Proprietary - Spread Capital

## Support

For issues or questions, contact the development team.
>>>>>>> 3a66b03 (Add gitignore to protect secrets)
