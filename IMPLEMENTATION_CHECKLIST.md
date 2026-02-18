# ✅ Cloud Deployment Checklist

## Pre-Setup Checklist

- [ ] Read IMPLEMENTATION_SUMMARY.md (this gives overview)
- [ ] Read QUICK_START.md (for basic setup)
- [ ] Verify all files are present (see File Inventory below)
- [ ] Have Python 3.8+ installed
- [ ] Have GitHub account (for cloud deployment)
- [ ] Have Google Cloud account (free tier available)

## Google Cloud Setup Checklist

### Project Creation
- [ ] Go to https://console.cloud.google.com/
- [ ] Click "Select a Project" → "New Project"
- [ ] Name: "Arrears Analysis System" (or similar)
- [ ] Click "Create"
- [ ] Wait for project to be created

### Enable Google Drive API
- [ ] In Cloud Console, search for "Google Drive API"
- [ ] Click on "Google Drive API"
- [ ] Click "Enable"
- [ ] Wait for API to be enabled

### Create Service Account
- [ ] Go to "APIs & Services" > "Credentials"
- [ ] Click "Create Credentials" > "Service Account"
- [ ] Service account name: "Arrears Analysis Bot"
- [ ] Click "Create and Continue"
- [ ] Skip optional steps
- [ ] Click "Done"

### Create and Download JSON Key
- [ ] Click the service account name
- [ ] Go to "Keys" tab
- [ ] Click "Add Key" > "Create new key"
- [ ] Select "JSON"
- [ ] Click "Create" (JSON file downloads)
- [ ] Save JSON file somewhere safe

### Create Google Drive Backup Folder
- [ ] Go to Google Drive: https://drive.google.com
- [ ] Create new folder: "Arrears Reports Backup"
- [ ] Open folder, copy folder ID from URL: `/folders/FOLDER_ID`
- [ ] Add folder ID to `.streamlit/secrets.toml`

### Share Folder with Service Account
- [ ] Open "Arrears Reports Backup" folder
- [ ] Click "Share"
- [ ] Paste service account email (from JSON client_email)
- [ ] Give "Editor" access
- [ ] Click "Share"

## Local Setup Checklist

### Install Dependencies
- [ ] Open terminal/PowerShell
- [ ] Navigate to project folder
- [ ] Run: `pip install -r requirements.txt`
- [ ] Wait for all packages to install
- [ ] Verify no errors

### Configure Secrets File
- [ ] Open `.streamlit/secrets.toml`
- [ ] Open downloaded Google Cloud JSON file
- [ ] Copy all content from JSON into `[google_cloud]` section
- [ ] Update `folder_id` with your Google Drive folder ID
- [ ] Save file

### Verify Secrets File
- [ ] Check `.streamlit/secrets.toml` is NOT in git (in .gitignore)
- [ ] Verify secrets.toml has valid content:
  - [ ] `[google_cloud]` section present
  - [ ] `project_id` filled in
  - [ ] `private_key` filled in
  - [ ] `client_email` filled in
  - [ ] `[google_drive]` section present
  - [ ] `folder_id` filled in

### Test Local Deployment
- [ ] Run: `streamlit run app.py`
- [ ] App opens at http://localhost:8501
- [ ] See "📁 Data Source" section at top
- [ ] File uploader visible
- [ ] No error messages in terminal

### Test File Upload
- [ ] Prepare sample CSV/Excel file with:
  - [ ] Account ID column
  - [ ] Member Name column
  - [ ] Product column
  - [ ] Arrears column (with numbers > 0)
  - [ ] Days column (optional)
  - [ ] Principle/Balance column (optional)
- [ ] Click "Choose a CSV or Excel file"
- [ ] Select your sample file
- [ ] Click "📤 Upload & Process File"
- [ ] Wait for processing
- [ ] See success message
- [ ] Data displays in dashboard
- [ ] Verify file appears in Google Drive

### Test All Features
- [ ] KPI cards display (Total Arrears, Defaulters, etc.)
- [ ] Charts render (Branch, Product, Aging)
- [ ] Filters work (Branch, Officer, Product, Aging)
- [ ] Worklists display (Call Back, Visit, Recovery)
- [ ] Rankings work (Branch Risk, Officer Performance)
- [ ] Can download CSV/Excel from worklists
- [ ] Trend charts display
- [ ] Can switch to "Load Local Data" (if local files present)

## GitHub Setup Checklist (For Cloud Deployment)

### Initialize Git Repository
- [ ] Open terminal in project folder
- [ ] Run: `git init`
- [ ] Run: `git add .`
- [ ] Run: `git commit -m "Cloud deployment setup"`
- [ ] Check git status: `git status`
- [ ] Verify `.streamlit/secrets.toml` is NOT listed

### Create GitHub Repository
- [ ] Go to https://github.com
- [ ] Click "+" > "New repository"
- [ ] Name: "christopher-arrears-analysis"
- [ ] Make it Private (for security)
- [ ] Do NOT initialize with README
- [ ] Click "Create repository"
- [ ] Copy the commands shown

### Connect and Push to GitHub
- [ ] Copy remote add command: `git remote add origin https://...`
- [ ] Run in terminal: `git branch -M main`
- [ ] Run: `git push -u origin main`
- [ ] Verify on GitHub that files appear
- [ ] Confirm `.streamlit/secrets.toml` is NOT in repo

## Streamlit Cloud Deployment Checklist

### Deploy App to Streamlit Cloud
- [ ] Go to https://share.streamlit.io/
- [ ] Click "Create app"
- [ ] Select your GitHub repository
- [ ] Set branch to "main"
- [ ] Set main file to "app.py"
- [ ] Click "Deploy!"
- [ ] Wait 2-5 minutes for deployment
- [ ] App appears in "My apps"

### Configure Secrets on Streamlit Cloud
- [ ] Click your deployed app
- [ ] Click "☰" menu > "Settings"
- [ ] Click "Secrets"
- [ ] Copy entire content from `.streamlit/secrets.toml`
- [ ] Paste into Streamlit Cloud Secrets editor
- [ ] Click "Save"
- [ ] Wait for app to redeploy

### Verify Cloud Deployment
- [ ] Click app URL to open
- [ ] See "📁 Data Source" section
- [ ] Try uploading sample file
- [ ] Verify file appears in Google Drive
- [ ] Check all features work
- [ ] No error messages in logs

## Testing & Validation Checklist

### Data Quality Tests
- [ ] Upload file with complete data
- [ ] Upload file with missing columns (should show error)
- [ ] Upload file with invalid format (should show error)
- [ ] Upload file with no arrears data (should show error)
- [ ] Upload large file (1000+ records)
- [ ] Verify all records load correctly

### Feature Tests
- [ ] KPIs calculate correctly
- [ ] Charts display with correct data
- [ ] Filters work independently
- [ ] Multiple filter selection works
- [ ] Clear filters returns to all data
- [ ] Date filter restricts data correctly
- [ ] Exports include filtered data only

### Google Drive Tests
- [ ] Files save to correct folder
- [ ] Filename includes timestamp
- [ ] Multiple uploads create separate files
- [ ] No duplicate files

### Performance Tests
- [ ] App loads in < 5 seconds (empty data)
- [ ] File upload completes in < 30 seconds
- [ ] Charts render within 10 seconds
- [ ] Filters apply within 5 seconds
- [ ] No lag in user interactions

## Documentation Checklist

- [ ] Read all README files
- [ ] Understand file structure
- [ ] Know where to find troubleshooting help
- [ ] Bookmark key documentation links
- [ ] Keep credentials safe
- [ ] Back up important files

## Security Checklist

- [ ] `.streamlit/secrets.toml` in `.gitignore` ✅
- [ ] Never committed secrets to GitHub ✅
- [ ] JSON credentials file stored safely ✅
- [ ] Google Drive folder only shared with service account ✅
- [ ] No hardcoded credentials in code ✅
- [ ] Repository is Private (if using sensitive data) ✅
- [ ] Service account has minimal permissions ✅

## Post-Deployment Checklist

### Monitor & Maintain
- [ ] App is accessible at Streamlit Cloud URL
- [ ] Team members can access the app
- [ ] Google Drive folder organized with backups
- [ ] Monitor for errors in logs
- [ ] Update dependencies monthly: `pip install --upgrade -r requirements.txt`

### Share with Team
- [ ] Share Streamlit Cloud app URL
- [ ] Provide instructions for use
- [ ] Set up training session if needed
- [ ] Establish data upload process
- [ ] Define backup/retention policy
- [ ] Document troubleshooting steps

### Maintenance
- [ ] Check Google Drive quota monthly
- [ ] Review backups periodically
- [ ] Update dependencies quarterly
- [ ] Monitor API usage
- [ ] Keep credentials secure
- [ ] Document any customizations

## Troubleshooting Checklist

If something doesn't work:

**File Upload Issues**
- [ ] Check file format (CSV or XLSX)
- [ ] Verify required columns present
- [ ] Check file isn't corrupted
- [ ] Try smaller sample file first
- [ ] Check file encoding (UTF-8)

**Google Drive Issues**
- [ ] Verify secrets.toml has correct credentials
- [ ] Check service account has folder access
- [ ] Verify Google Drive API is enabled
- [ ] Check folder ID is correct
- [ ] Verify authentication not expired

**Chart/Display Issues**
- [ ] Refresh the page
- [ ] Clear browser cache
- [ ] Check data has required columns
- [ ] Verify numeric columns have values
- [ ] Check for duplicate column names

**Cloud Deployment Issues**
- [ ] Check .gitignore includes secrets.toml
- [ ] Verify secrets configured in Streamlit Cloud
- [ ] Check app logs for errors
- [ ] Wait for redeploy to complete
- [ ] Try manual redeploy from dashboard

## Success Criteria

You'll know everything is working when:

✅ **Local Environment**
- [ ] App runs without errors: `streamlit run app.py`
- [ ] File uploader accepts CSV/Excel files
- [ ] Data processes and displays in dashboard
- [ ] Files appear in Google Drive
- [ ] All analytics features work

✅ **Cloud Environment**
- [ ] App accessible at Streamlit Cloud URL
- [ ] File upload works in cloud
- [ ] Google Drive backup works
- [ ] Team can access shared URL
- [ ] All features work same as local

✅ **Team Adoption**
- [ ] Users can upload files independently
- [ ] Users understand the workflow
- [ ] Analytics meet business needs
- [ ] Data backups secure in Google Drive
- [ ] Adoption smooth and productive

---

## Quick Reference

| Phase | Estimated Time | Key Document |
|-------|-----------------|--------------|
| Google Cloud Setup | 30 minutes | SETUP_GUIDE.md |
| Local Testing | 15 minutes | QUICK_START.md |
| Cloud Deployment | 20 minutes | DEPLOY_TO_CLOUD.md |
| Full Setup & Testing | 2-3 hours | All guides |

---

## Questions? Need Help?

1. **Quick questions** → QUICK_START.md
2. **Setup problems** → SETUP_GUIDE.md  
3. **Cloud issues** → CLOUD_DEPLOYMENT.md
4. **Deployment issues** → DEPLOY_TO_CLOUD.md
5. **General overview** → IMPLEMENTATION_SUMMARY.md

---

## Next Step

✅ You are here: Reviewing this checklist  
⏭️ Next: Start from "Google Cloud Setup Checklist" above

Good luck! 🚀

---

**Tracking Progress**: Print this checklist and check off items as you complete them!

**Save This**: Bookmark or save this checklist for future reference.

**Estimated Total Time**: 2-3 hours for complete setup and testing

**Status**: Ready to implement! 🎉
