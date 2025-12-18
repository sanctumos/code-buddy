# GitHub Organization Webhook Setup Guide

## 🎯 Overview
This guide walks you through setting up a GitHub organization webhook to capture ALL events (issues, PRs, pushes, releases, etc.) from your entire organization.

## 📋 Prerequisites
- GitHub organization admin access
- Your webhook endpoint URL (e.g., `https://your-server.com/webhook`)
- A secret token (any random string)

## 🔧 Step-by-Step Setup

### **Option A: GitHub CLI (Recommended - Fastest)**

#### **Prerequisites:**
- GitHub CLI installed (`gh` command)
- Organization owner permissions
- Your webhook endpoint URL ready

#### **Step 1: Install GitHub CLI (if not already installed)**
```bash
# Windows (using winget)
winget install GitHub.cli

# Or download from: https://cli.github.com/
```

#### **Step 2: Authenticate with GitHub**
```bash
# Login to GitHub
gh auth login

# Ensure you have organization webhook permissions
gh auth refresh --scopes admin:org_hook
```

#### **Step 3: Create Organization Webhook**

**Option A: Use the automated script (Recommended)**
```bash
# Linux/Mac
chmod +x scripts/setup-webhook.sh
./scripts/setup-webhook.sh YOUR_ORG_NAME https://your-server.com/webhook your_secret_token

# Windows PowerShell
.\scripts\setup-webhook.ps1 -OrgName "YOUR_ORG_NAME" -WebhookUrl "https://your-server.com/webhook" -Secret "your_secret_token"
```

**Option B: Manual CLI command**
```bash
# Create webhook for ALL events (recommended)
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /orgs/YOUR_ORG_NAME/hooks \
  -f name='web' \
  -f config='{"url":"https://your-server.com/webhook","content_type":"json","secret":"your_secret_token_here"}' \
  -f events='["*"]' \
  -F active=true
```

**Replace:**
- `YOUR_ORG_NAME` with your organization name
- `https://your-server.com/webhook` with your webhook URL
- `your_secret_token_here` with your secret token

#### **Step 4: Verify Webhook Creation**
```bash
# List all organization webhooks
gh api /orgs/YOUR_ORG_NAME/hooks
```

#### **Alternative: Specific Events Only**
```bash
# Create webhook for specific events only
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /orgs/YOUR_ORG_NAME/hooks \
  -f name='web' \
  -f config='{"url":"https://your-server.com/webhook","content_type":"json","secret":"your_secret_token_here"}' \
  -f events='["issues","pull_request","push","release","repository"]' \
  -F active=true
```

### **Option B: Web Interface (Manual)**

#### **Step 1: Navigate to Organization Settings**

1. **Go to your GitHub organization page**
   - URL: `https://github.com/YOUR_ORG_NAME`
   - Replace `YOUR_ORG_NAME` with your actual organization name

2. **Click on "Settings" tab**
   - Located in the top navigation bar
   - You must be an organization owner to see this

### **Step 2: Access Webhooks Section**

1. **In the left sidebar, click "Webhooks"**
   - Under the "Code and automation" section
   - If you don't see this, you need organization owner permissions

2. **Click "Add webhook" button**
   - Green button in the top right

### **Step 3: Configure Webhook Settings**

#### **Payload URL**
```
https://your-server.com/webhook
```
- Replace with your actual webhook endpoint URL
- Must be HTTPS (GitHub requires SSL)
- Must be publicly accessible

#### **Content Type**
Select: `application/json`
- This sends JSON payloads (easier to parse)

#### **Secret**
```
your_secret_token_here
```
- Generate a random string (e.g., `gh_webhook_secret_2024_xyz789`)
- **IMPORTANT**: Save this secret - you'll need it in your code
- This is used for HMAC signature verification

#### **SSL Verification**
Leave checked: `✓ Enable SSL verification`
- GitHub requires HTTPS endpoints

### **Step 4: Select Events**

#### **Option A: Capture Everything (Recommended)**
- Select: **"Send me everything"**
- This captures ALL events across your organization
- Includes: Issues, PRs, Pushes, Releases, Repository events, Team changes, etc.

#### **Option B: Select Specific Events**
- Select: **"Let me select individual events"**
- Check the events you want:
  - ✅ `Issues` (issue opened, closed, assigned, etc.)
  - ✅ `Pull requests` (PR opened, closed, merged, etc.)
  - ✅ `Pushes` (code commits, branch updates)
  - ✅ `Releases` (new releases published)
  - ✅ `Repository` (repo created, deleted, archived)
  - ✅ `Team` (team membership changes)
  - ✅ `Organization` (org member changes)
  - ✅ `Workflow runs` (CI/CD pipeline events)
  - ✅ `Deployments` (deployment status)
  - ✅ `Security advisories` (security alerts)

### **Step 5: Save Webhook**

1. **Click "Add webhook"**
2. **Verify the webhook appears in your list**
3. **Test the webhook** (see testing section below)

## 🧪 Testing Your Webhook

### **Method 1: GitHub's Built-in Test**
1. **Click on your webhook** in the webhooks list
2. **Scroll down to "Recent Deliveries"**
3. **Click "Redeliver"** on any recent delivery
4. **Check your server logs** to see if the request arrived

### **Method 2: Manual Test**
1. **Create a test issue** in any repository in your organization
2. **Check your webhook endpoint** - you should receive a POST request
3. **Verify the signature** using your secret token

## 🔍 Webhook Payload Example

When an issue is created, you'll receive a POST request like this:

```json
{
  "action": "opened",
  "issue": {
    "id": 123456789,
    "number": 42,
    "title": "Bug in authentication system",
    "body": "The login form doesn't validate passwords correctly",
    "state": "open",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "user": {
      "login": "developer123",
      "id": 987654321
    }
  },
  "repository": {
    "id": 111222333,
    "name": "my-awesome-project",
    "full_name": "YOUR_ORG/my-awesome-project",
    "html_url": "https://github.com/YOUR_ORG/my-awesome-project"
  },
  "organization": {
    "login": "YOUR_ORG",
    "id": 444555666
  }
}
```

## 🔐 Security Headers

GitHub sends these headers with every webhook:

```
X-GitHub-Event: issues
X-GitHub-Delivery: 12345678-1234-1234-1234-123456789abc
X-Hub-Signature-256: sha256=abc123def456...
```

**Important**: Always verify the `X-Hub-Signature-256` header using your secret token!

## 🚨 Troubleshooting

### **Common Issues:**

#### **"Webhook not receiving requests"**
- ✅ Check your endpoint URL is correct and accessible
- ✅ Ensure your server is running and listening on the right port
- ✅ Verify HTTPS is working (GitHub requires SSL)

#### **"Invalid signature" errors**
- ✅ Double-check your secret token matches exactly
- ✅ Ensure you're computing HMAC-SHA256 correctly
- ✅ Verify you're using the raw request body (not parsed JSON)

#### **"Permission denied" when setting up webhook**
- ✅ You need organization owner permissions
- ✅ Contact your organization admin to grant access

#### **"Webhook deliveries failing"**
- ✅ Check your server logs for error messages
- ✅ Ensure your endpoint returns HTTP 200 for successful processing
- ✅ Verify your server can handle the request size (some payloads are large)

## 📊 Monitoring Webhook Health

### **GitHub Webhook Dashboard**
- Go to your webhook settings
- Check "Recent Deliveries" section
- Green checkmarks = successful deliveries
- Red X marks = failed deliveries

### **Response Codes**
- `200` = Success (webhook processed)
- `4xx` = Client error (bad request, unauthorized)
- `5xx` = Server error (internal server error)

## 🔄 Webhook Management

### **CLI Management (Recommended)**

#### **List All Webhooks**
```bash
gh api /orgs/YOUR_ORG_NAME/hooks
```

#### **Get Specific Webhook Details**
```bash
gh api /orgs/YOUR_ORG_NAME/hooks/WEBHOOK_ID
```

#### **Update Webhook**
```bash
gh api \
  --method PATCH \
  -H "Accept: application/vnd.github+json" \
  /orgs/YOUR_ORG_NAME/hooks/WEBHOOK_ID \
  -f config='{"url":"https://new-url.com/webhook","content_type":"json","secret":"new_secret"}' \
  -f events='["issues","pull_request"]'
```

#### **Delete Webhook**
```bash
gh api \
  --method DELETE \
  /orgs/YOUR_ORG_NAME/hooks/WEBHOOK_ID
```

#### **Test Webhook Delivery**
```bash
gh api \
  --method POST \
  /orgs/YOUR_ORG_NAME/hooks/WEBHOOK_ID/tests
```

### **Web Interface Management**

#### **Disable Webhook**
- Go to webhook settings
- Uncheck "Active" checkbox
- Webhook stops receiving events but stays configured

#### **Delete Webhook**
- Go to webhook settings
- Click "Delete webhook"
- Confirms deletion

#### **Update Webhook**
- Click on webhook name
- Modify settings as needed
- Click "Update webhook"

## 📝 Next Steps

After setting up your webhook:

1. **Implement your webhook endpoint** (see project plan Phase 1, Task 2)
2. **Add HMAC signature verification** (20 lines of code)
3. **Test with real GitHub events**
4. **Set up monitoring and logging**
5. **Configure event filtering** (optional)

## 🎯 Success Criteria

Your webhook setup is complete when:
- ✅ Webhook appears in GitHub organization settings
- ✅ Recent deliveries show successful requests (green checkmarks)
- ✅ Your server receives and processes webhook payloads
- ✅ HMAC signature verification works correctly
- ✅ You can see events from multiple repositories in your organization

