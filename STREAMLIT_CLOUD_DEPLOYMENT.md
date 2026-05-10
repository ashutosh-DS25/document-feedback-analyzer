# Streamlit Cloud Deployment

## Files ready for deployment

- `app.py` is the Streamlit entry file.
- `requirements.txt` contains the Python packages Streamlit Cloud installs.
- `.streamlit/secrets.example.toml` shows the secrets you need to add in Streamlit Cloud.
- `.gitignore` keeps local secrets, virtualenv files, and cache files out of GitHub.

## Streamlit Cloud steps

1. Push this project to a GitHub repository.
2. Go to Streamlit Cloud and create a new app.
3. Select the GitHub repository, branch, and set the main file path to `app.py`.
4. Open app settings, then Secrets, and add:

```toml
OPENROUTER_API_KEY="your_real_openrouter_key"
OPENROUTER_MODEL="deepseek/deepseek-chat-v3-0324"
ALERT_WEBHOOK_URL=""
```

5. Deploy the app.

## Alert webhook note

`localhost` URLs do not work on Streamlit Cloud. If you want complaint alert notifications, replace `ALERT_WEBHOOK_URL` with a public production webhook URL from your automation tool.
