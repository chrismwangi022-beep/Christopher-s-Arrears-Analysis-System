"""
Data loader for Spread Capital Arrears Analysis System
Handles CSV/Excel loading, Branch/Loan Officer extraction, and forward-fill logic
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import re

from .constants import (
    DATA_FOLDER,
    COLUMN_PATTERNS,
    DEFAULT_COLUMNS,
    HEADER_KEYWORDS,
)

MASTER_DATASET_PATH = os.path.join("data", "master_dataset.parquet")

def detect_column_by_pattern(df: pd.DataFrame, patterns: List[str], default_col: Optional[int] = None) -> Optional[int]:
    """Detect column index by matching header patterns."""
    if df.empty:
        return default_col
    
    # Check header row (first row)
    header_row = df.iloc[0] if len(df) > 0 else pd.Series()
    
    for idx, col_name in enumerate(header_row):
        col_str = str(col_name).lower() if pd.notna(col_name) else ""
        for pattern in patterns:
            if pattern.lower() in col_str:
                return idx
    
    # If header detection fails, check first few rows
    for row_idx in range(min(3, len(df))):
        for col_idx in range(min(len(df.columns), 20)):  # Check first 20 columns
            cell_value = str(df.iloc[row_idx, col_idx]).lower() if pd.notna(df.iloc[row_idx, col_idx]) else ""
            for pattern in patterns:
                if pattern.lower() in cell_value:
                    return col_idx
    
    return default_col


def extract_branch_from_filename(filename: str) -> str:
    """Extract branch name from filename (first word before space or dot)."""
    name = Path(filename).stem
    parts = name.split()
    if parts:
        return parts[0].lower()
    parts = name.split('.')
    if parts:
        return parts[0].lower()
    return "unknown"


def extract_date_from_filename(filename: str) -> Optional[datetime.date]:
    """Try to parse a date from the filename using common patterns.

    Falls back to None if no parseable date is found.
    """
    # Common date patterns: YYYY-MM-DD, YYYY.MM.DD, DD-MM-YYYY, DD.MM.YYYY, YYYYMMDD
    patterns = [r"(\d{4}[-\.]\d{2}[-\.]\d{2})", r"(\d{2}[-\.]\d{2}[-\.]\d{4})", r"(\d{8})"]
    for p in patterns:
        m = re.search(p, filename)
        if m:
            s = m.group(1)
            # Try a range of common formats including dot-separated dates
            for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d-%m-%Y", "%d.%m.%Y", "%Y%m%d", "%d%m%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    continue
    return None


def extract_branch_and_officer(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """
    Extract Branch and Loan Officer from row headers and forward-fill.
    
    Logic:
    - Scan rows for "branch :" or "loan officer :" in columns A or B
    - Extract value from the other column
    - Forward-fill until next header row
    """
    df = df.copy()
    df['Branch'] = None
    df['Loan_Officer'] = None
    
    current_branch = extract_branch_from_filename(filename)
    current_officer = None
    
    # Scan rows for headers
    for idx in range(len(df)):
        row = df.iloc[idx]
        col_a = str(row.iloc[0]).lower() if len(row) > 0 and pd.notna(row.iloc[0]) else ""
        col_b = str(row.iloc[1]).lower() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
        
        combined = col_a + " " + col_b
        
        # Check for Branch header
        for keyword in HEADER_KEYWORDS["branch"]:
            if keyword.lower() in combined:
                # Extract branch from the other column
                if keyword.lower() in col_a:
                    branch_val = str(row.iloc[1]).strip() if len(row) > 1 else ""
                else:
                    branch_val = str(row.iloc[0]).strip()
                
                if branch_val and branch_val.lower() not in ["none", "nan", ""]:
                    current_branch = branch_val.lower().strip()
                break
        
        # Check for Loan Officer header
        for keyword in HEADER_KEYWORDS["loan_officer"]:
            if keyword.lower() in combined:
                # Extract officer from the other column
                if keyword.lower() in col_a:
                    officer_val = str(row.iloc[1]).strip() if len(row) > 1 else ""
                else:
                    officer_val = str(row.iloc[0]).strip()
                
                if officer_val and officer_val.lower() not in ["none", "nan", ""]:
                    current_officer = officer_val.lower().strip()
                break
        
        # Assign current values
        df.iloc[idx, df.columns.get_loc('Branch')] = current_branch
        if current_officer:
            df.iloc[idx, df.columns.get_loc('Loan_Officer')] = current_officer
    
    # Forward-fill Branch and Loan_Officer
    df['Branch'] = df['Branch'].ffill()
    df['Loan_Officer'] = df['Loan_Officer'].ffill()
    
    return df


def _extract_records_from_df(df: pd.DataFrame, filename: str, report_date: Optional[datetime.date]) -> pd.DataFrame:
    """Core logic to process a raw DataFrame and extract valid arrears records."""
    # Detect columns
    arrears_col = detect_column_by_pattern(df, COLUMN_PATTERNS["arrears"], DEFAULT_COLUMNS["arrears"])
    principle_col = detect_column_by_pattern(df, COLUMN_PATTERNS["principle"], DEFAULT_COLUMNS["principle"])
    total_balance_col = detect_column_by_pattern(df, COLUMN_PATTERNS["total_balance"], DEFAULT_COLUMNS["total_balance"])
    days_col = detect_column_by_pattern(df, COLUMN_PATTERNS["days"], DEFAULT_COLUMNS["days"])
    product_col = detect_column_by_pattern(df, COLUMN_PATTERNS["product"], DEFAULT_COLUMNS["product"])
    account_id_col = detect_column_by_pattern(df, COLUMN_PATTERNS["account_id"], DEFAULT_COLUMNS["account_id"])
    member_name_col = detect_column_by_pattern(df, COLUMN_PATTERNS.get("member_name", []), DEFAULT_COLUMNS.get("member_name"))

    # Find first numeric row in arrears column to identify potential data rows
    data_rows = []
    for idx in range(len(df)):
        row = df.iloc[idx]
        if arrears_col is not None and arrears_col < len(row):
            arrears_val = row.iloc[arrears_col]
            try:
                float_val = float(str(arrears_val).replace(',', '').replace(' ', ''))
                if float_val > 0:  # A simple heuristic to find data
                    data_rows.append(idx)
            except (ValueError, AttributeError):
                continue

    if not data_rows:
        return pd.DataFrame()

    # Build result dataframe
    result_data = []
    for idx in data_rows:
        row = df.iloc[idx]

        # --- DATA CLEANING: ensure this is a real account row ---
        member_no_raw = str(row.iloc[account_id_col]).strip() if account_id_col is not None and account_id_col < len(row) else ""
        member_name_raw = str(row.iloc[member_name_col]).strip() if member_name_col is not None and member_name_col < len(row) else ""
        product_raw = str(row.iloc[product_col]).strip() if product_col is not None and product_col < len(row) else ""

        # Apply cleaning rules:
        if not member_name_raw or member_name_raw.lower() in ["nan", "none", ""]: continue
        if member_no_raw and any(word in member_no_raw.lower() for word in ["branch", "total"]): continue
        if not product_raw or product_raw.lower() in ["nan", "none", ""]: continue

        # At this point we consider the row a valid loan account
        record = {
            'Branch': str(row['Branch']) if pd.notna(row['Branch']) else extract_branch_from_filename(filename),
            'Loan_Officer': str(row['Loan_Officer']) if pd.notna(row['Loan_Officer']) else None,
            'MemberName': member_name_raw,
            'Report_Date': report_date,
        }

        # Extract values with error handling
        def extract_numeric(col_idx, key):
            if col_idx is not None and col_idx < len(row):
                try:
                    val_str = str(row.iloc[col_idx]).replace(',', '').replace(' ', '')
                    return float(val_str) if val_str else None
                except (ValueError, AttributeError):
                    return None
            return None

        record['Arrears'] = extract_numeric(arrears_col, 'Arrears') or 0.0
        record['Principle'] = extract_numeric(principle_col, 'Principle')
        record['TotalBalance'] = extract_numeric(total_balance_col, 'TotalBalance')

        days_val = extract_numeric(days_col, 'Days')
        record['Days'] = int(days_val) if days_val is not None else None

        record['Product'] = product_raw if product_raw else "Unspecified"

        if account_id_col is not None and account_id_col < len(row):
            account_val = str(row.iloc[account_id_col]).strip()
            record['AccountID'] = account_val if account_val and account_val.lower() not in ["none", "nan", ""] else None
        else:
            record['AccountID'] = None

        result_data.append(record)

    if not result_data:
        return pd.DataFrame()

    result_df = pd.DataFrame(result_data)

    # Fill missing Principle/TotalBalance with fallbacks
    if 'Principle' in result_df.columns:
        result_df['Principle'] = pd.to_numeric(result_df['Principle'], errors='coerce').fillna(result_df['Arrears'])
    else:
        result_df['Principle'] = result_df['Arrears']

    if 'TotalBalance' in result_df.columns:
        result_df['TotalBalance'] = pd.to_numeric(result_df['TotalBalance'], errors='coerce').fillna(
            result_df['Principle'] + result_df['Arrears']
        )
    else:
        result_df['TotalBalance'] = result_df['Principle'] + result_df['Arrears']

    # Ensure numeric columns are properly typed
    for col in ['Arrears', 'Principle', 'TotalBalance']:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0.0)

    return result_df


def load_and_process_file(file_path: str) -> pd.DataFrame:
    """Load a single CSV or Excel file and process it."""
    filename = os.path.basename(file_path)
    # Attempt to determine report date from filename, otherwise fallback to file modified time
    file_report_date = extract_date_from_filename(filename)
    if file_report_date is None:
        try:
            file_mtime = os.path.getmtime(file_path)
            file_report_date = datetime.fromtimestamp(file_mtime).date()
        except Exception:
            file_report_date = None
    
    try:
        # Load file
        if file_path.lower().endswith('.csv'):
            print(f"  DEBUG: Reading CSV: {filename}")
            df = pd.read_csv(file_path, header=None, encoding='latin1')
        else:
            print(f"  DEBUG: Reading XLSX: {filename}")
            df = pd.read_excel(file_path, header=None)
        
        print(f"  DEBUG: Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Fill NaN with empty strings for easier string operations
        df = df.fillna('')
        
        # Extract Branch and Loan Officer context
        df = extract_branch_and_officer(df, filename)
        
        # Delegate processing to the core logic function
        return _extract_records_from_df(df, filename, file_report_date)
        
    except Exception as e:
        print(f"ERROR loading {filename}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_all_data() -> pd.DataFrame:
    """Load all CSV and Excel files from the DATA_FOLDER."""
    print(f"DEBUG: DATA_FOLDER = {DATA_FOLDER}")
    print(f"DEBUG: DATA_FOLDER exists: {os.path.exists(DATA_FOLDER)}")
    
    if not os.path.exists(DATA_FOLDER):
        print(f"ERROR: Data folder not found: {DATA_FOLDER}")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        print(f"DEBUG: Workspace root directory: {os.path.dirname(DATA_FOLDER)}")
        return pd.DataFrame()
    
    all_dataframes = []
    files = [f for f in os.listdir(DATA_FOLDER) 
             if f.lower().endswith(('.csv', '.xlsx', '.xls')) 
             and "Movement Report" not in f]
    
    print(f"DEBUG: Found {len(files)} data files in {DATA_FOLDER}")
    print(f"DEBUG: Files found: {files}")
    
    if not files:
        print(f"ERROR: No data files found in {DATA_FOLDER}")
        return pd.DataFrame()
    
    print(f"Processing {len(files)} files...")
    
    for filename in files:
        file_path = os.path.join(DATA_FOLDER, filename)
        print(f"  Loading: {filename}")
        df = load_and_process_file(file_path)
        if not df.empty:
            all_dataframes.append(df)
            print(f"    ✓ Loaded {filename}: {len(df)} records")
            print(f"    Columns: {list(df.columns)}")
        else:
            print(f"    ✗ No records loaded from {filename}")
    
    if not all_dataframes:
        print(f"ERROR: No data loaded from any files")
        return pd.DataFrame()
    
    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Clean up Branch and Loan_Officer
    combined_df['Branch'] = combined_df['Branch'].astype(str).str.lower().str.strip()
    combined_df['Loan_Officer'] = combined_df['Loan_Officer'].astype(str).str.lower().str.strip()
    combined_df['Loan_Officer'] = combined_df['Loan_Officer'].replace(['none', 'nan', ''], None)
    
    # Ensure numeric columns
    numeric_cols = ['Arrears', 'Principle', 'TotalBalance']
    for col in numeric_cols:
        if col in combined_df.columns:
            combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0.0)
    
    print(f"\nSUCCESS: Total records loaded: {len(combined_df)}")
    print(f"Final columns: {list(combined_df.columns)}")
    return combined_df


def process_uploaded_file(uploaded_file, branch_name: Optional[str] = None) -> pd.DataFrame:
    """
    Process an uploaded file from Streamlit file_uploader.
    
    Args:
        uploaded_file: Streamlit UploadedFile object from st.file_uploader
        branch_name: Optional branch name to override/assign
        
    Returns:
        Processed DataFrame ready for analysis
    """
    if uploaded_file is None:
        return pd.DataFrame()
    
    try:
        # Determine file type
        filename = uploaded_file.name.lower()
        report_date = extract_date_from_filename(uploaded_file.name)
        
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None, encoding='latin1')
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file, header=None)
        else:
            return pd.DataFrame()
        
        # Fill NaN with empty strings
        df = df.fillna('')
        
        # Extract branch and officer
        df = extract_branch_and_officer(df, uploaded_file.name)
        
        # Override branch if provided
        if branch_name:
            df['Branch'] = branch_name.lower().strip()

        # Delegate to the core processing function
        return _extract_records_from_df(df, uploaded_file.name, report_date)
        
    except Exception as e:
        print(f"Error processing uploaded file: {e}")
        return pd.DataFrame()

def load_master_dataset() -> pd.DataFrame:
    """
    Loads the master dataset from Parquet format.
    If Parquet doesn't exist, builds it from historical CSV/XLSX files using load_all_data().
    """
    # Check if parquet exists and is healthy
    if os.path.exists(MASTER_DATASET_PATH):
        df = pd.read_parquet(MASTER_DATASET_PATH, engine='pyarrow')
        
        # HEURISTIC: Check for incomplete initialization (1 branch vs multiple source files)
        raw_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        if df['Branch'].nunique() <= 1 and len(raw_files) > 1:
            print("DEBUG: Master Parquet appears incomplete (Single Branch). Rebuilding from source...")
        else:
            print(f"DEBUG: Loading existing master dataset from {MASTER_DATASET_PATH}")
            return df

    # Initial Build or Forced Rebuild
    print(f"DEBUG: Initializing master dataset from all files in {DATA_FOLDER}...")
    df = load_all_data()
    if not df.empty:
        os.makedirs(os.path.dirname(MASTER_DATASET_PATH), exist_ok=True)
        df.to_parquet(MASTER_DATASET_PATH, index=False, engine='pyarrow')
        print(f"DEBUG: Master dataset initialized and saved to {MASTER_DATASET_PATH}")
    return df

def append_to_master_dataset(new_df: pd.DataFrame):
    """
    Appends new records to the master parquet file to keep the persistent dataset updated.
    """
    if new_df.empty:
        return

    # Ensure directory exists
    os.makedirs(os.path.dirname(MASTER_DATASET_PATH), exist_ok=True)

    if os.path.exists(MASTER_DATASET_PATH):
        try:
            existing_df = pd.read_parquet(MASTER_DATASET_PATH, engine='pyarrow')
            # Append and enforce integrity by removing potential duplicates
            updated_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates()
            updated_df.to_parquet(MASTER_DATASET_PATH, index=False, engine='pyarrow')
            print(f"DEBUG: Successfully appended {len(new_df)} records to {MASTER_DATASET_PATH}")
        except Exception as e:
            print(f"ERROR appending to master dataset: {e}")
    else:
        new_df.to_parquet(MASTER_DATASET_PATH, index=False, engine='pyarrow')
        print(f"DEBUG: Master dataset created at {MASTER_DATASET_PATH} with initial records.")
