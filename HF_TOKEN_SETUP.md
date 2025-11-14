# HF_TOKEN Quick Setup Guide

**5-Minute Setup for GitHub → HuggingFace Auto-Sync**

## Step 1: Get Your HuggingFace Token (2 minutes)

1. Visit: https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Name: `arena-improver-sync`
4. Permissions: Select **"Write"** ✅
5. Click **"Generate token"**
6. **COPY THE TOKEN NOW** (you won't see it again!)

## Step 2: Add to GitHub Secrets (2 minutes)

1. Visit: https://github.com/clduab11/arena-improver/settings/secrets/actions
2. Click **"New repository secret"**
3. Name: `HF_TOKEN`
4. Value: Paste your token from Step 1
5. Click **"Add secret"**

## Step 3: Test the Sync (1 minute)

### Option A: Automatic (Recommended)
- Just push to the `main` branch
- GitHub Actions will auto-sync to HF Space

### Option B: Manual Trigger
1. Visit: https://github.com/clduab11/arena-improver/actions/workflows/sync-to-hf.yml
2. Click **"Run workflow"**
3. Select branch: `main`
4. Click **"Run workflow"**

## Step 4: Configure HF Space API Keys

Your Space needs these API keys to function:

### Required Keys
1. Go to: https://huggingface.co/spaces/MCP-1st-Birthday/vawlrath/settings
2. Scroll to **"Repository secrets"**
3. Add these secrets:

| Secret Name | Get From | Required |
|-------------|----------|----------|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | ✅ Yes |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | ✅ Yes |
| `TAVILY_API_KEY` | https://tavily.com/ | ⚠️ Recommended |
| `EXA_API_KEY` | https://exa.ai/ | ⚠️ Recommended |

## Verification

After setup, verify everything works:

1. **Check Sync Status**: https://github.com/clduab11/arena-improver/actions
2. **Visit Your Space**: https://huggingface.co/spaces/MCP-1st-Birthday/vawlrath
3. **Check Status Tab**: Should show all API keys as "✓ Configured"
4. **Test API**: Try the "API Documentation" tab

## Troubleshooting

### Sync Failed?
- Check `HF_TOKEN` is in GitHub Secrets
- Verify token has **Write** permissions
- Check GitHub Actions logs for errors

### Space Shows "Missing API Keys"?
- Add API keys to HF Space secrets (not GitHub!)
- Restart the Space after adding secrets
- Check the "Status" tab to verify

### Still Broken?
See full guide: [docs/HF_DEPLOYMENT.md](docs/HF_DEPLOYMENT.md)

---

*"Stop procrastinating and set up your tokens. It takes 5 minutes."*
— **Vawlrathh, The Small'n**
