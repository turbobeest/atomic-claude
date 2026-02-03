# AWS SSO Configuration for ATOMIC CLAUDE

Guide for corporate/government environments using AWS SSO with rotating credentials.

## Overview

Corporate AWS environments typically use:
- **AWS SSO** (Single Sign-On) with temporary credentials
- **AWS Profiles** configured via AWS CLI
- **Credential rotation** (credentials expire after 8-12 hours)

ATOMIC CLAUDE supports profile-based authentication for seamless SSO integration.

## Setup Steps

### 1. Configure AWS Profile (One-time)

Configure your AWS SSO profile using AWS CLI:

```bash
aws configure sso
```

**Prompts:**
```
SSO session name: bedrock-dev
SSO start URL: https://your-org.awsapps.com/start
SSO region: us-gov-west-1
SSO registration scopes: sso:account:access
```

This creates `~/.aws/config`:
```ini
[profile bedrock-dev]
sso_start_url = https://your-org.awsapps.com/start
sso_region = us-gov-west-1
sso_account_id = 123456789012
sso_role_name = BedrockDeveloper
region = us-gov-west-1
output = json
```

### 2. Create .env File

Create `.env` in your project root:

```bash
cd /path/to/your-project
nano .env
```

**Contents:**
```bash
AWS_PROFILE=bedrock-dev
AWS_REGION=us-gov-west-1
CLAUDE_CODE_USE_BEDROCK=1
ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'
```

**Note:** Use the corporate template:
```bash
cp .env.corporate .env
```

### 3. Configure llm-preferences.md

Edit `initialization/llm-preferences.md`:

```markdown
# PRIMARY PROVIDER CHAIN
aws-bedrock        # AWS Bedrock (active)
ollama             # Local fallback

# MODEL PREFERENCES
us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0   # Primary
```

## Daily Workflow

### Authenticate Before Each Session

SSO credentials expire after 8-12 hours. Authenticate at the start of each session:

```bash
# 1. Login via SSO
aws sso login --profile bedrock-dev

# 2. Verify authentication
aws sts get-caller-identity --profile bedrock-dev

# 3. Run ATOMIC CLAUDE
./main.sh run 0
```

### If Credentials Expire Mid-Session

When you see `ExpiredToken` errors:

```bash
# Re-authenticate
aws sso login --profile bedrock-dev

# Resume from where you left off
./main.sh run 2  # Resume Phase 2, for example
```

## Task 001 Validation

Task 001 automatically validates your AWS setup:

```
✓ AWS Bedrock profile loaded: bedrock-dev
  Region: us-gov-west-1
  Model: us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0
  ✓ Profile authenticated
```

Or if credentials expired:
```
✓ AWS Bedrock profile loaded: bedrock-dev
  Region: us-gov-west-1
  Model: us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0
  ⚠  Profile not authenticated
     Run: aws sso login --profile bedrock-dev
```

## Model Selection (GovCloud)

Available models in `us-gov-west-1`:

```bash
# Sonnet 4.5 (Recommended - Best balance)
us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0

# Opus 4.5 (Maximum reasoning)
us-gov.anthropic.claude-opus-4-5-20251101-v1:0

# Haiku 4.5 (Fast, cost-effective)
us-gov.anthropic.claude-haiku-4-5-20251101-v1:0

# Haiku 3.0 (Fallback)
us-gov.anthropic.claude-3-haiku-20240307-v1:0
```

## IAM Permissions Required

Your IAM role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws-us-gov:bedrock:us-gov-west-1::foundation-model/anthropic.claude-*"
      ]
    }
  ]
}
```

Contact your AWS administrator if you lack these permissions.

## Troubleshooting

### "Profile not found"

**Error:** `The config profile (bedrock-dev) could not be found`

**Solution:**
```bash
# List configured profiles
aws configure list-profiles

# If missing, configure SSO
aws configure sso
```

### "ExpiredToken"

**Error:** `An error occurred (ExpiredToken) when calling the InvokeModel operation`

**Solution:**
```bash
# Re-authenticate
aws sso login --profile bedrock-dev

# Continue pipeline
./main.sh run 0
```

### "AccessDeniedException"

**Error:** `An error occurred (AccessDeniedException) when calling the InvokeModel operation`

**Solution:**
- Your IAM role lacks `bedrock:InvokeModel` permission
- Contact AWS administrator to grant access
- Verify model is available in your region

### "No providers available"

**Error:** Task 001 shows no providers detected

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify AWS_PROFILE is set
grep AWS_PROFILE .env

# Check authentication
aws sts get-caller-identity --profile bedrock-dev
```

## Fallback to Ollama

If Bedrock is unavailable, configure Ollama fallback in `llm-preferences.md`:

```markdown
# FALLBACK BEHAVIOR
## API → Ollama Fallback
true         # Recommended if Ollama enabled
```

Start Ollama:
```bash
ollama serve
```

ATOMIC CLAUDE will automatically fall back to local models if Bedrock fails.

## Security Best Practices

1. **Never commit .env** - It's gitignored by default
2. **Use SSO, not static keys** - Temporary credentials are more secure
3. **Rotate regularly** - SSO enforces automatic rotation
4. **Least privilege** - Only request necessary Bedrock permissions
5. **Audit access** - Monitor CloudTrail for Bedrock API calls

## Corporate Template

Use `.env.corporate` as your starting point:

```bash
cp .env.corporate .env
# Edit AWS_PROFILE to match your organization's profile name
```

## For More Help

- **AWS SSO Documentation**: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html
- **Bedrock User Guide**: https://docs.aws.amazon.com/bedrock/latest/userguide/
- **ATOMIC CLAUDE Quick Start**: `docs/QUICK-START.md`
