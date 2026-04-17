# TTG Survey Analytics — Streamlit App

## Deploy in 5 minutes

### Step 1 — Put this folder on GitHub
1. Go to github.com → click the **+** → **New repository**
2. Name it `ttg-survey-analytics`, set to **Private**, click **Create**
3. Click **uploading an existing file**
4. Drag ALL files from this folder into the upload area (`app.py`, `requirements.txt`, and the `.streamlit/secrets.toml`)
5. Click **Commit changes**

### Step 2 — Deploy on Streamlit
1. Go to **share.streamlit.io** → sign in with your GitHub account
2. Click **Create app**
3. Select your `ttg-survey-analytics` repo
4. Main file path: `app.py`
5. Click **Deploy**

### Step 3 — Add your API key (once)
1. In Streamlit → your app → **Settings** → **Secrets**
2. Paste this (with your real key):
```
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```
3. Save — the app restarts automatically

### Done
Your app is live at `https://yourname-ttg-survey-analytics.streamlit.app`

---

## How to use

1. Upload your survey CSV
2. Upload your PDF data key (optional — auto-extracts question labels using AI)
3. Click **Build Dashboard**
4. Browse all questions in the left sidebar
5. Select any demographic breakout from the dropdown
6. Toggle 2-way on/off

## Sharing with clients / team
- Share the Streamlit URL directly
- They upload their own CSV — nothing is stored server-side
- Or send them a specific survey: upload the CSV yourself, then share a screenshot/export

## For each new survey
Just go to the URL, upload the new CSV, done. No redeployment needed.
