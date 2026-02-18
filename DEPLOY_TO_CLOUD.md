# Deploy to Streamlit Cloud - Step by Step

## Prerequisites

- GitHub account (create at github.com if needed)
- Streamlit Cloud account (share.streamlit.io)
- Google Cloud credentials configured in `.streamlit/secrets.toml`
- All app code ready and tested locally

## Step 1: Initialize Git Repository

If not already a git repo:

```bash
cd "C:\Users\ADMIN\Desktop\Christopher\Christopher's Arrears Analysis System"
git init
```

## Step 2: Create .gitignore Entry (CRITICAL!)

Make sure `.streamlit/secrets.toml` is in `.gitignore`:

```bash
# Check if .gitignore already includes secrets
findstr ".streamlit" .gitignore

# If not found, add it:
echo .streamlit/secrets.toml >> .gitignore
```

**Verify**: Open `.gitignore` and confirm:
```
.streamlit/secrets.toml
.streamlit/logger.toml
.streamlit/*.toml
```

## Step 3: Commit Code to Git

```bash
# Stage all files
git add .

# Commit with message
git commit -m "Cloud deployment: Add file upload and Google Drive integration"

# Verify what's being tracked
git status
```

**Verify that `.streamlit/secrets.toml` is NOT listed as tracked**

## Step 4: Create GitHub Repository

1. Go to **github.com** and sign in
2. Click **+** (top right) → **New repository**
3. Fill in:
   - **Repository name**: `christopher-arrears-analysis` (or your preference)
   - **Description**: "Spread Capital Arrears Analysis System - Cloud Ready"
   - **Public** or **Private** (recommend Private for sensitive data)
   - Do NOT initialize with README (you have one)
4. Click **Create repository**

## Step 5: Connect Local Repo to GitHub

GitHub will show commands after creating. Use:

```bash
# Add remote (replace YOURNAME and YOURREPO)
git remote add origin https://github.com/YOURNAME/christopher-arrears-analysis.git

# Rename branch to main (if using master)
git branch -M main

# Verify remote
git remote -v
```

## Step 6: Push Code to GitHub

```bash
# First time push
git push -u origin main

# Subsequent pushes
git push
```

**Verify** on github.com:
- Files appear in repository
- `secrets.toml` is NOT in the repo
- All Python files are present

## Step 7: Deploy to Streamlit Cloud

1. Go to **share.streamlit.io**
2. Click **Create app**
3. Fill in deployment details:
   - **GitHub repository**: `YOURNAME/christopher-arrears-analysis`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **Deploy!**

**Wait** 2-5 minutes for deployment to complete

## Step 8: Configure Secrets on Streamlit Cloud

1. Your app is now live! Click on your app in **My apps**
2. Click the **☰** (hamburger menu) → **Settings**
3. Click **Secrets**
4. **Copy-paste the entire content** of your `.streamlit/secrets.toml`:

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

5. Click **Save** (app will automatically redeploy with secrets)

## Step 9: Verify Deployment

1. Wait for app to finish deploying
2. Click app URL to open it
3. Test file upload functionality
4. Verify Google Drive save works
5. Check all charts and features work

## Step 10: Continuous Updates

For future updates:

```bash
# Make changes locally
# Test with: streamlit run app.py

# Commit and push
git add .
git commit -m "Description of changes"
git push

# Streamlit Cloud auto-deploys within 1-2 minutes!
```

---

## Troubleshooting Deployment

### "Repository not found" error
- Verify GitHub repository is created
- Confirm you have push access
- Check authentication with: `git remote -v`

### "Branch not found" error
- Push main branch: `git push -u origin main`
- Verify on GitHub that main branch exists
- Try different branch name if needed

### Secrets not working
- Verify format in Streamlit Cloud Secrets editor
- Check spelling of `google_cloud` and `google_drive` sections
- Invalid JSON will show error message
- Re-enter if unsure

### File upload still not working
- Confirm secrets are saved (check app logs)
- Verify service account email has folder access
- Check Google Drive folder ID is correct
- Review CLOUD_DEPLOYMENT.md > Troubleshooting

### App crashes on load
- Check **Logs** tab in Streamlit Cloud
- Common issues:
  - Missing dependencies in requirements.txt
  - Secrets not configured
  - Google API error
- Fix locally, push to GitHub, or re-add secrets

### Very slow deployment
- First deployment can take 5+ minutes
- Building Docker image in background
- Check **Logs** tab for progress
- Wait and refresh if needed

---

## Managing Your Cloud App

### View Logs
- Settings → **Logs** tab
- Shows real-time app output
- Check for errors here

### App Settings
- Settings → General
- Can pause, unpause, or delete app
- Change branch or main file
- Edit app name/description

### Check Usage
- Settings → **Logs**
- View requests and performance
- Monitor for issues

### Update App Code
```bash
git add .
git commit -m "Update description"
git push
# Auto-deploys in 1-2 minutes
```

### Rollback to Previous Version
```bash
# View commit history
git log --oneline

# Reset to previous commit
git reset --hard COMMIT_HASH

# Force push
git push -f origin main

# App will redeploy with old version
```

---

## Security Reminders

✅ **DO THIS**:
- Keep `.streamlit/secrets.toml` in `.gitignore`
- Use strong GitHub passwords/2FA
- Review who has repository access
- Monitor Google Drive backups regularly
- Keep dependencies updated

❌ **DON'T DO THIS**:
- Don't commit credentials to GitHub
- Don't share Google Cloud JSON file
- Don't push `.streamlit/secrets.toml`
- Don't use user personal credentials
- Don't set repo to public if using real data

---

## Post-Deployment Checklist

- [ ] App deployed to Streamlit Cloud
- [ ] Secrets configured
- [ ] File upload works
- [ ] Google Drive backup confirmed
- [ ] All features tested
- [ ] Shared URL with stakeholders
- [ ] Documented deployment process
- [ ] Set up monitoring/alerts
- [ ] Plan backup strategy

---

## Getting Help

**Streamlit Cloud Issues**: https://discuss.streamlit.io/  
**GitHub Issues**: Click Issues tab in your repository  
**Google Cloud Support**: https://cloud.google.com/support

---

## Next: Share Your App!

Copy your Streamlit Cloud app URL and share with:
- Team members
- Stakeholders
- Finance department
- Anyone who needs arrears analysis

**URL Format**: `https://share.streamlit.io/YOUR_GITHUB_USERNAME/christopher-arrears-analysis/main/app.py`

---

**Deployed**: February 18, 2026  
**Status**: Cloud Ready ✅
