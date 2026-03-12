# Bing Ads MCP Server

MCP server for querying Microsoft Advertising (Bing Ads) data from Claude Code. Gives Claude access to account info, campaigns, ad groups, ads, keywords, and performance reports.

## Prerequisites

- Python 3.10+
- [pipx](https://pipx.pypa.io/stable/installation/) (`brew install pipx && pipx ensurepath`)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- Access to a Microsoft Advertising account

## Quick Start

### 1. Clone the repo

```bash
git clone git@github.com:Shopify/bing-ads-mcp.git
cd bing-ads-mcp
```

### 2. Register an Azure AD app (one-time, team can share)

> If a teammate has already registered an app, ask them for the **client_id** and **developer_token** — skip to step 3.
>
> **Don't have access?** Reach out to the martech team (Marius specifically) or Sal Rapisarldi to get the app ID / client_id.

1. Go to [Azure Portal - App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
3. Name it something like `bing-ads-mcp`
4. Under **Redirect URI**, select **Public client/native** and set it to:
   ```
   https://login.microsoftonline.com/common/oauth2/nativeclient
   ```
5. Click **Register** and copy the **Application (client) ID**

### 3. Get a Developer Token

Go to [Microsoft Advertising Developer Portal](https://developers.ads.microsoft.com/Account) and request/copy your developer token.

### 4. Create your credentials file

```bash
cp bing-ads.yaml.example bing-ads.yaml
```

Edit `bing-ads.yaml` and fill in your `client_id` and `developer_token`:

```yaml
client_id: "your-azure-app-client-id"
developer_token: "your-developer-token"
refresh_token: ""   # Will be auto-saved in the next step
customer_id: ""     # Optional
account_id: ""      # Optional
```

### 5. Install and authenticate

```bash
pipx install -e .
export BING_ADS_CREDENTIALS=$(pwd)/bing-ads.yaml
bing-ads-mcp-auth
```

This opens your browser for Microsoft OAuth consent. Once approved, the refresh token is saved automatically to `bing-ads.yaml`.

### 6. Register with Claude Code

```bash
claude mcp add bing-ads-mcp \
  -e BING_ADS_CREDENTIALS=$HOME/bing-ads-mcp/bing-ads.yaml \
  -- bing-ads-mcp
```

### 7. Verify it works

Open Claude Code and ask:

```
List my Bing Ads accounts
```

You should see a list of Microsoft Advertising accounts.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_accounts` | List all accessible Microsoft Advertising accounts |
| `get_campaigns` | Get campaigns for an account (filter by type/status) |
| `get_ad_groups` | Get ad groups for a campaign |
| `get_ads` | Get ads for an ad group |
| `get_keywords` | Get keywords for an ad group |
| `get_report` | Run performance reports (campaign, ad group, keyword, search query, geographic, etc.) |

## Example Queries

- "List all active Growth Paid Search accounts"
- "Show me campaigns in account 12345678"
- "Get a campaign performance report for the last 30 days"
- "What are the top keywords by spend in campaign X?"
- "Pull a search query report for the North America account last week"

## Troubleshooting

### "MCP server not found" in Claude Code
Make sure `pipx` binaries are on your PATH:
```bash
pipx ensurepath
```
Then restart your terminal and re-run the `claude mcp add` command.

### "Authentication failed" or expired token
Re-run the auth flow:
```bash
export BING_ADS_CREDENTIALS=$HOME/bing-ads-mcp/bing-ads.yaml
bing-ads-mcp-auth
```

### Manually generating a refresh token (if OAuth browser flow doesn't work)

If `bing-ads-mcp-auth` fails to open a browser or gets stuck (e.g. running on a remote machine, WSL, or headless environment), you can generate the refresh token manually:

1. **Build the authorization URL** — open this in any browser, replacing `YOUR_CLIENT_ID`:

   ```
   https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient&scope=https://ads.microsoft.com/msads.manage offline_access
   ```

2. **Sign in and consent** — after granting access, you'll be redirected to a blank page. Copy the full URL from the address bar. It will look like:

   ```
   https://login.microsoftonline.com/common/oauth2/nativeclient?code=M.C507_BAY.2.U.0a1b2c3d...
   ```

3. **Extract the code** — copy everything after `code=` (up to any `&` if present).

4. **Exchange the code for a refresh token** using `curl`:

   ```bash
   curl -X POST https://login.microsoftonline.com/common/oauth2/v2.0/token \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "grant_type=authorization_code" \
     -d "code=PASTE_CODE_HERE" \
     -d "redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient" \
     -d "scope=https://ads.microsoft.com/msads.manage offline_access"
   ```

5. **Copy the `refresh_token`** from the JSON response and paste it into your `bing-ads.yaml` file:

   ```yaml
   refresh_token: "0.AVQA..."
   ```

6. **Verify** by running `claude` and asking it to list your Bing Ads accounts.

### Check MCP server status
```bash
claude mcp list
```
