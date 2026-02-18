# Spread Capital Arrears Analysis System - Cloud Deployment Guide

## Overview

Your Streamlit app has been updated for cloud deployment with the following enhancements:

- **File Upload**: Upload CSV/Excel files directly in the app instead of relying on local folders
- **Google Drive Integration**: Automatically save uploaded files to Google Drive for backup and version control
- **Cloud-Ready Secrets Management**: Use `st.secrets` for secure credential handling
- **Flexible Data Loading**: Switch between uploaded files and local data loading
- **Maintains Existing Features**: All analytics, visualizations, and UI remain unchanged

## Setup Instructions

### 1. Local Development Setup

#### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 2: Configure Google Cloud Credentials

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project (e.g., "Arrears Analysis System")

2. **Enable Google Drive API**:
   - Search for "Google Drive API" in the console
   - Click "Enable"

3. **Create a Service Account**:
   - Go to **APIs & Services** > **Credentials**
   - Click **Create Credentials** > **Service Account**
   - Enter service account name (e.g., "Arrears Analysis Bot")
   - Click **Create and Continue**
   - Skip optional steps and click **Done**

4. **Create Service Account Key**:
   - Click on the created service account
   - Go to **Keys** tab
   - Click **Add Key** > **Create new key**
   - Select **JSON** format
   - Click **Create** (downloads a JSON file)

5. **Update `.streamlit/secrets.toml`**:
   ```bash
   # Create .streamlit directory if it doesn't exist
   mkdir .streamlit
   ```
   - Open the downloaded service account JSON file
   - Copy all its contents
   - Navigate to `.streamlit/secrets.toml` in your project
   - Update the `[google_cloud]` section with your JSON credentials

   Example:
   ```toml
   [google_cloud]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-key-id"
   private_key = "your-private-key"
   client_email = "your-email@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-cert-url"
   
   [google_drive]
   folder_id = "YOUR_GOOGLE_DRIVE_FOLDER_ID"
   ```

6. **Share Google Drive Folder with Service Account**:
   - Create a folder in Google Drive for storing backups (e.g., "Arrears Reports Backup")
   - Get its Folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Share the folder:
     - Open the folder in Google Drive
     - Click **Share**
     - Paste the service account email (from `client_email` in JSON)
     - Grant **Editor** access
     - Click **Share**

7. **Update `[google_drive]` folder_id**:
   - In `.streamlit/secrets.toml`, replace `YOUR_GOOGLE_DRIVE_FOLDER_ID` with the actual folder ID

#### Step 3: Run Locally

```bash
streamlit run app.py
```

Access the app at `http://localhost:8501`

### 2. Deploy to Streamlit Cloud

#### Step 1: Push Code to GitHub

```bash
git init
git add .
git commit -m "Cloud deployment setup"
git push origin main
```

**IMPORTANT**: Make sure `.streamlit/secrets.toml` is in `.gitignore`:
```bash
echo ".streamlit/secrets.toml" >> .gitignore
```

#### Step 2: Deploy to Streamlit Cloud

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Click **"New app"**
3. Connect your GitHub repository
4. Select the branch and main file (`app.py`)
5. Click **Deploy**

#### Step 3: Configure Secrets on Streamlit Cloud

1. In your deployed app, click on your account icon > **Settings**
2. Click on your app > **Secrets**
3. Copy-paste the contents of `.streamlit/secrets.toml` into the Secrets editor
4. Click **Save**

Your app will automatically redeploy with the secrets configured.

## Features

### File Upload & Processing
- Upload CSV/Excel files with arrears data
- Automatic data validation and processing
- Real-time feedback on processing status

### Google Drive Integration
- Automatic backup of uploaded files to Google Drive
- Timestamped file naming for version control
- Secure credential management using service account

### Data Management
- **Toggle Data Source**: Switch between uploaded files and local data
- **Flexible Column Mapping**: Automatically detects columns by pattern matching
- **Data Cleaning**: Removes invalid rows, normalizes values

### Analytics Features (Unchanged)
All original features remain intact:
- KPI Dashboard (Total Arrears, Defaulters, Average DPD, PAR%, Total Principal)
- Charts (Arrears by Branch, Arrears by Product, Aging Buckets)
- Strategic Recommendations with priority levels
- Action-Level Worklist (Call Backs, Physical Visits, Recovery Escalations)
- Performance Rankings (Branch Risk, Product Risk, Officer Performance)
- Portfolio Distribution Analysis
- Arrears Trend Movement tracking
- Daily Arrears Movement charts

## File Format Requirements

Uploaded CSV/Excel files should contain columns (name variation acceptable):
- **Account ID**: MemberNo, Member No, Account ID, AccountID, Client ID
- **Member Name**: MemberName, Member Name, Client Name, Customer Name, Borrower Name
- **Product**: Product, Loan Type, Loan Product, Product Type
- **Arrears**: Arrears, Arrear, Overdue, Outstanding Balance, Balance Due
- **Principle**: Principle, Principal, Loan Amount, Disbursed, Disbursement
- **Days**: Days, Overdue Days, Past Due, Days Overdue, Aging
- **Total Balance**: Total Balance, TotalBalance, Outstanding Balance, Loan Balance

Optional columns:
- **Branch**: Auto-extracted from filename or column
- **Loan Officer**: Auto-extracted from column

## Troubleshooting

### Google Drive Authentication Fails
- Verify credentials in `.streamlit/secrets.toml`
- Ensure service account email has access to the destination folder
- Check that Google Drive API is enabled in Cloud Console

### File Upload Not Working
- Ensure file format is CSV or Excel
- Check file contains required columns (arrears, product, member name)
- Review file for data quality issues

### Column Detection Issues
- Add explicit sheet with proper headers at the top
- Use standard column names listed in "File Format Requirements"
- Check that data starts on row with proper header

### Data Not Persisting After Rerun
- Uploaded data is stored in Streamlit session state
- Refresh the page to clear session
- Re-upload the file if needed

## Next Steps

1. **Test Locally**: Upload a sample file and verify data processing
2. **Verify Google Drive**: Check that files are being saved to your Google Drive folder
3. **Deploy to Cloud**: Follow deployment steps and test in production
4. **Monitor Usage**: Check Google Drive folder periodically for backups

## Security Notes

- **Never commit `.streamlit/secrets.toml`** to version control
- Use separate service accounts for development and production
- Regularly rotate service account keys
- Limit service account permissions to only required Google Drive folders
- Monitor Google Drive folder for unauthorized access

## Support & Maintenance

- Keep dependencies updated: `pip install -r requirements.txt --upgrade`
- Check Google Cloud Console for API quotas
- Monitor app logs in Streamlit Cloud dashboard
- Backup Google Drive folder regularly

---

**Last Updated**: February 18, 2026
**Version**: 2.0 - Cloud Ready
