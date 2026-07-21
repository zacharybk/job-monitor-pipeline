"""One-time Gmail OAuth. Run once after placing .gmail_client_secret.json:

    /Users/zach/.venv/bin/python -m agent.gmail_auth

Opens a browser for you to authorize. Never sees your password; saves a local
token to agent/.gmail_token.json (gitignored).
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from agent.gmail_drafts import CLIENT_SECRET_PATH, TOKEN_PATH, SCOPES


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"Gmail authorized. Token saved to {TOKEN_PATH}")


if __name__ == "__main__":
    main()
