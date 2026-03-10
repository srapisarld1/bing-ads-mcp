"""One-time OAuth authorization code flow for Bing Ads authentication.

Usage:
    bing-ads-mcp-auth

This opens your browser for Microsoft OAuth consent. After sign-in,
you paste the redirect URL back into the terminal. The refresh token
is then saved to the bing-ads.yaml config file.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser

import yaml

_AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_SCOPE = "https://ads.microsoft.com/msads.manage offline_access"
_REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"


def run_auth_setup() -> None:
    config_path = os.environ.get("BING_ADS_CREDENTIALS")
    if not config_path:
        print("Error: BING_ADS_CREDENTIALS environment variable not set.")
        print("Set it to the path of your bing-ads.yaml file.")
        print("Example: export BING_ADS_CREDENTIALS=~/bing-ads-mcp/bing-ads.yaml")
        sys.exit(1)

    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    client_id = config.get("client_id", "")
    if not client_id or client_id == "YOUR_AZURE_APP_CLIENT_ID":
        print("Error: client_id not configured in", config_path)
        sys.exit(1)

    print()
    print("=" * 60)
    print("Bing Ads MCP - OAuth Setup")
    print("=" * 60)
    print()

    # Build authorization URL and open browser
    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": _REDIRECT_URI,
        "response_mode": "query",
        "scope": _SCOPE,
    })
    auth_url = f"{_AUTHORIZE_URL}?{auth_params}"

    print("Opening browser for Microsoft sign-in...")
    print()
    webbrowser.open(auth_url)

    print("After signing in, the browser will redirect to a blank page.")
    print("Copy the FULL URL from your browser's address bar and paste it below.")
    print()
    redirect_url = input("Paste the redirect URL here: ").strip()

    if not redirect_url:
        print("Error: No URL provided.")
        sys.exit(1)

    # Extract authorization code from the redirect URL
    parsed = urllib.parse.urlparse(redirect_url)
    params = urllib.parse.parse_qs(parsed.query)

    if "error" in params:
        desc = params.get("error_description", params["error"])[0]
        print(f"Error: {desc}")
        sys.exit(1)

    if "code" not in params:
        print("Error: No authorization code found in the URL.")
        print("Make sure you copied the full URL from the address bar.")
        sys.exit(1)

    auth_code = params["code"][0]

    # Exchange authorization code for tokens
    print()
    print("Exchanging code for tokens...")

    token_data = urllib.parse.urlencode({
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": _REDIRECT_URI,
        "scope": _SCOPE,
    }).encode()

    token_req = urllib.request.Request(_TOKEN_URL, data=token_data)
    try:
        token_resp = urllib.request.urlopen(token_req)
        tokens = json.loads(token_resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = json.loads(e.read().decode())
        print(f"Error: {error_body.get('error_description', error_body.get('error'))}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("Error: No refresh token in response.")
        sys.exit(1)

    # Save to config
    config["refresh_token"] = refresh_token

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print()
    print("Success! Refresh token saved to", config_path)
    print()
    print("You can now start the MCP server:")
    print(f"  BING_ADS_CREDENTIALS={config_path} bing-ads-mcp")
    print()


if __name__ == "__main__":
    run_auth_setup()
