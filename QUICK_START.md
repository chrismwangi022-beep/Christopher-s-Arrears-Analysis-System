# Cloud Deployment Setup - Quick Start Guide

## What's New

Your Streamlit app has been upgraded for cloud deployment with:

✅ **File Upload Feature** - Upload CSV/Excel files directly in the app  
✅ **Google Drive Integration** - Auto-save uploaded files to Google Drive  
✅ **Secure Credentials** - Use st.secrets instead of local JSON files  
✅ **All Original Features Intact** - Analytics, charts, and reports unchanged  

## Quick Setup (5 minutes)

### Prerequisites

- Python 3.8+
- Google Cloud account (free tier available)
- Google Drive account

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Get Google Cloud Credentials

1. Create Google Cloud project: https://console.cloud.google.com/
2. Enable Google Drive API
3. Create Service Account (APIs & Services > Credentials > Create Credentials)
4. Create JSON key for the service account
5. Keep the downloaded JSON safe

### Step 3: Configure Secrets

#### For Local Testing:

Create `.streamlit/secrets.toml`:
```toml
[google_cloud]
type = "service_account"
project_id = "your-project-id"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "YOUR_PRIVATE_KEY"
client_email = "your-email@your-project.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CERT_URL"

[google_drive]
folder_id = "YOUR_FOLDER_ID"
```

(Copy values from the downloaded service account JSON)

#### For Streamlit Cloud:

1. Deploy to Streamlit Cloud
2. Go to app settings > Secrets
3. Paste the same configuration above

### Step 4: Create Google Drive Folder

1. Create a folder in Google Drive for backups
2. Get folder ID from URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`
3. Share folder with service account email (give Editor access)
4. Update folder_id in secrets

### Step 5: Run the App

```bash
streamlit run app.py
```

## How to Use

### Upload Data

1. Click "📁 Data Source" section
2. Click "Choose a CSV or Excel file"
3. Select your arrears report
4. Click "📤 Upload & Process File"
5. File is validated and saved to Google Drive

### Switch Data Source
- Use "📂 Load Local Data" button to use local folder data
- Use file uploader to switch back to uploaded files

### Access Analytics
All features work exactly as before:
- KPI Dashboard with 5 key metrics
- Charts by Branch, Product, Aging
- Strategic Recommendations
- Action-Level Worklist
- Performance Rankings
- Trend Analysis

## File Format

Your CSV/Excel files should have columns like:
- MemberNo, Account ID, AccountID
- MemberName, Member Name, Client Name
- Product, Loan Product, Loan Type
- Arrears, Overdue, Outstanding Balance
- Principle, Principal, Loan Amount
- Days, Overdue Days, Days Past Due
- Branch (optional)
- Loan Officer (optional)

System auto-detects column names by keywords.

## Troubleshooting

**File not uploading?**
- Check file format is CSV or XLSX
- Verify file has required columns
- Ensure data rows have numeric arrears values

**Google Drive save failing?**
- Check credentials in .streamlit/secrets.toml
- Verify service account email has folder access
- Confirm Google Drive API is enabled

**Column detection issues?**
- Add clear headers with standard names
- Check first row has column names
- Use common naming (arrears, product, member name)

## Files Modified/Added

```
NEW:
- src/google_drive_handler.py      (Google Drive operations)
- .streamlit/secrets.toml          (Credentials template)
- CLOUD_DEPLOYMENT.md              (Full deployment guide)
- QUICK_START.md                   (This file)

UPDATED:
- app.py                           (File uploader + Google Drive integration)
- src/data_loader.py               (process_uploaded_file function)
- requirements.txt                 (New dependencies added)
- .gitignore                       (Protect secrets)
```

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Get Google Cloud credentials
3. ✅ Create `.streamlit/secrets.toml` with your credentials
4. ✅ Test locally: `streamlit run app.py`
5. ✅ Upload a sample file to test
6. ✅ Verify file appears in Google Drive
7. ✅ Deploy to Streamlit Cloud (push to GitHub)
8. ✅ Add secrets on Streamlit Cloud dashboard

## Need Help?

See `CLOUD_DEPLOYMENT.md` for:
- Detailed setup instructions
- Troubleshooting guide
- Security best practices
- Deployment to production

---

**Version**: 2.0 - Cloud Ready  
**Last Updated**: February 18, 2026
